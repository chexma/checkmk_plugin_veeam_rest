<#
.SYNOPSIS
    Veeam Backup & Replication REST API Agent Plugin for CheckMK

.DESCRIPTION
    This agent plugin connects to the local Veeam B&R REST API and collects
    monitoring data for backup jobs, task sessions, repositories, proxies,
    managed servers, license info, and more.

    This is an alternative to the special agent approach - the plugin runs
    locally on the Veeam server and communicates with localhost, avoiding
    the need to open firewall ports to the CheckMK server.

.NOTES
    Installation:
    - Deploy via Agent Bakery, or
    - Copy to C:\ProgramData\checkmk\agent\plugins\
    - Create config at C:\ProgramData\checkmk\agent\config\veeam_rest.json

.LINK
    https://helpcenter.veeam.com/references/vbr/13/rest/1.3-rev1/tag/SectionOverview
#>

#Requires -Version 5.1

# =============================================================================
# CONFIGURATION
# =============================================================================

$script:ConfigDir = if ($env:MK_CONFDIR) { $env:MK_CONFDIR } else { "C:\ProgramData\checkmk\agent\config" }
$script:ApiVersion = "1.3-rev1"
$script:Errors = @()

# Default configuration
$script:Config = @{
    username     = ""
    password     = ""
    port         = 9419
    no_cert_check = $true
    timeout      = 60
    sections     = @("jobs", "tasks", "repositories", "proxies")
    session_age  = 86400
}

function Read-PluginConfig {
    <#
    .SYNOPSIS
        Read plugin configuration from JSON file
    #>
    $configFile = Join-Path $script:ConfigDir "veeam_rest.json"

    if (-not (Test-Path $configFile)) {
        return $false
    }

    try {
        $jsonConfig = Get-Content $configFile -Raw -Encoding UTF8 | ConvertFrom-Json

        # Update config with values from JSON
        if ($jsonConfig.username) { $script:Config.username = $jsonConfig.username }
        if ($jsonConfig.password) { $script:Config.password = $jsonConfig.password }
        if ($jsonConfig.port) { $script:Config.port = [int]$jsonConfig.port }
        if ($null -ne $jsonConfig.no_cert_check) { $script:Config.no_cert_check = [bool]$jsonConfig.no_cert_check }
        if ($jsonConfig.timeout) { $script:Config.timeout = [int]$jsonConfig.timeout }
        if ($jsonConfig.sections) { $script:Config.sections = @($jsonConfig.sections) }
        if ($jsonConfig.session_age) { $script:Config.session_age = [int]$jsonConfig.session_age }

        return $true
    }
    catch {
        return $false
    }
}

# =============================================================================
# SSL HANDLING
# =============================================================================

function Disable-SslVerification {
    <#
    .SYNOPSIS
        Disable SSL certificate verification for self-signed certs
    #>
    if ($script:Config.no_cert_check) {
        # PowerShell 5.1 way
        if (-not ([System.Management.Automation.PSTypeName]'TrustAllCertsPolicy').Type) {
            Add-Type @"
using System.Net;
using System.Security.Cryptography.X509Certificates;
public class TrustAllCertsPolicy : ICertificatePolicy {
    public bool CheckValidationResult(
        ServicePoint srvPoint, X509Certificate certificate,
        WebRequest request, int certificateProblem) {
        return true;
    }
}
"@
        }
        [System.Net.ServicePointManager]::CertificatePolicy = New-Object TrustAllCertsPolicy
        [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    }
}

# =============================================================================
# API CLIENT
# =============================================================================

function Get-VeeamAuthToken {
    <#
    .SYNOPSIS
        Acquire OAuth2 access token using password grant
    .OUTPUTS
        Access token string or $null on failure
    #>
    param(
        [string]$BaseUrl,
        [string]$Username,
        [string]$Password
    )

    $tokenUrl = "$BaseUrl/api/oauth2/token"

    $body = @{
        grant_type = "password"
        username   = $Username
        password   = $Password
    }

    $headers = @{
        "Content-Type"  = "application/x-www-form-urlencoded"
        "x-api-version" = $script:ApiVersion
    }

    try {
        $response = Invoke-RestMethod -Uri $tokenUrl `
            -Method Post `
            -Body $body `
            -Headers $headers `
            -TimeoutSec $script:Config.timeout `
            -ErrorAction Stop

        return $response.access_token
    }
    catch {
        $script:Errors += @{
            section = "authentication"
            error   = "Authentication failed: $($_.Exception.Message)"
        }
        return $null
    }
}

function Invoke-VeeamApi {
    <#
    .SYNOPSIS
        Make authenticated GET request to Veeam API
    .PARAMETER Endpoint
        API endpoint path (e.g., "/api/v1/jobs/states")
    .PARAMETER Token
        OAuth2 access token
    .PARAMETER BaseUrl
        API base URL
    .PARAMETER Params
        Optional query parameters hashtable
    #>
    param(
        [string]$Endpoint,
        [string]$Token,
        [string]$BaseUrl,
        [hashtable]$Params = @{}
    )

    $url = "$BaseUrl$Endpoint"

    if ($Params.Count -gt 0) {
        $queryString = ($Params.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }) -join "&"
        $url = "$url?$queryString"
    }

    $headers = @{
        "Authorization" = "Bearer $Token"
        "x-api-version" = $script:ApiVersion
        "Accept"        = "application/json"
    }

    try {
        $response = Invoke-RestMethod -Uri $url `
            -Method Get `
            -Headers $headers `
            -TimeoutSec $script:Config.timeout `
            -ErrorAction Stop

        return $response
    }
    catch {
        throw "API request failed for $Endpoint`: $($_.Exception.Message)"
    }
}

function Get-VeeamPaginatedData {
    <#
    .SYNOPSIS
        Get all items from a paginated endpoint
    #>
    param(
        [string]$Endpoint,
        [string]$Token,
        [string]$BaseUrl,
        [hashtable]$Params = @{},
        [int]$Limit = 500
    )

    $allItems = @()
    $skip = 0

    do {
        $requestParams = $Params.Clone()
        $requestParams["skip"] = $skip
        $requestParams["limit"] = $Limit

        $response = Invoke-VeeamApi -Endpoint $Endpoint -Token $Token -BaseUrl $BaseUrl -Params $requestParams

        $data = @()
        if ($response.data) {
            $data = @($response.data)
        }
        $allItems += $data

        $total = if ($response.pagination.total) { $response.pagination.total } else { $data.Count }

        if (($skip + $data.Count) -ge $total -or $data.Count -eq 0) {
            break
        }

        $skip += $Limit
    } while ($true)

    return $allItems
}

# =============================================================================
# DATA COLLECTION FUNCTIONS
# =============================================================================

function Get-VeeamServerInfo {
    param([string]$Token, [string]$BaseUrl)

    try {
        $data = Invoke-VeeamApi -Endpoint "/api/v1/serverInfo" -Token $Token -BaseUrl $BaseUrl
        return $data
    }
    catch {
        $script:Errors += @{ section = "server"; error = $_.Exception.Message }
        return $null
    }
}

function Get-VeeamJobs {
    param([string]$Token, [string]$BaseUrl, [string]$ServerName)

    try {
        $jobs = Get-VeeamPaginatedData -Endpoint "/api/v1/jobs/states" -Token $Token -BaseUrl $BaseUrl

        # Enrich job data
        $now = [DateTime]::UtcNow
        foreach ($job in $jobs) {
            $job | Add-Member -NotePropertyName "backupServer" -NotePropertyValue $ServerName -Force

            if ($job.lastRun) {
                try {
                    $lastRunDt = [DateTime]::Parse($job.lastRun).ToUniversalTime()
                    $ageSeconds = [int]($now - $lastRunDt).TotalSeconds
                    $job | Add-Member -NotePropertyName "lastRunAgeSeconds" -NotePropertyValue $ageSeconds -Force
                }
                catch {
                    $job | Add-Member -NotePropertyName "lastRunAgeSeconds" -NotePropertyValue $null -Force
                }
            }
        }

        return $jobs
    }
    catch {
        $script:Errors += @{ section = "jobs"; error = $_.Exception.Message }
        return $null
    }
}

function Get-VeeamTasks {
    param([string]$Token, [string]$BaseUrl, [string]$ServerName, [string]$CreatedAfter)

    try {
        $params = @{}
        if ($CreatedAfter) {
            $params["createdAfterFilter"] = $CreatedAfter
        }

        $tasks = Get-VeeamPaginatedData -Endpoint "/api/v1/taskSessions" -Token $Token -BaseUrl $BaseUrl -Params $params

        # Enrich task data
        $now = [DateTime]::UtcNow
        foreach ($task in $tasks) {
            $task | Add-Member -NotePropertyName "backupServer" -NotePropertyValue $ServerName -Force

            # Calculate backup age
            if ($task.endTime) {
                try {
                    $endTimeDt = [DateTime]::Parse($task.endTime).ToUniversalTime()
                    $ageSeconds = [int]($now - $endTimeDt).TotalSeconds
                    $task | Add-Member -NotePropertyName "backupAgeSeconds" -NotePropertyValue $ageSeconds -Force
                }
                catch {
                    $task | Add-Member -NotePropertyName "backupAgeSeconds" -NotePropertyValue $null -Force
                }
            }

            # Parse duration to seconds
            if ($task.progress -and $task.progress.duration) {
                try {
                    $durationStr = $task.progress.duration
                    $parts = $durationStr -split ":"

                    if ($parts.Count -eq 3) {
                        $days = 0
                        $hours = 0

                        if ($parts[0] -match "\.") {
                            $dayHour = $parts[0] -split "\."
                            $days = [int]$dayHour[0]
                            $hours = [int]$dayHour[1]
                        }
                        else {
                            $hours = [int]$parts[0]
                        }

                        $minutes = [int]$parts[1]
                        $seconds = [int][Math]::Floor([double]$parts[2])

                        $totalSeconds = $days * 86400 + $hours * 3600 + $minutes * 60 + $seconds
                        $task | Add-Member -NotePropertyName "durationSeconds" -NotePropertyValue $totalSeconds -Force
                    }
                }
                catch {
                    $task | Add-Member -NotePropertyName "durationSeconds" -NotePropertyValue $null -Force
                }
            }
        }

        return $tasks
    }
    catch {
        $script:Errors += @{ section = "tasks"; error = $_.Exception.Message }
        return $null
    }
}

function Get-VeeamSessions {
    param([string]$Token, [string]$BaseUrl, [string]$CreatedAfter)

    try {
        $params = @{}
        if ($CreatedAfter) {
            $params["createdAfterFilter"] = $CreatedAfter
        }

        return Get-VeeamPaginatedData -Endpoint "/api/v1/sessions" -Token $Token -BaseUrl $BaseUrl -Params $params
    }
    catch {
        $script:Errors += @{ section = "sessions"; error = $_.Exception.Message }
        return $null
    }
}

function Get-VeeamRepositories {
    param([string]$Token, [string]$BaseUrl)

    try {
        return Get-VeeamPaginatedData -Endpoint "/api/v1/backupInfrastructure/repositories/states" -Token $Token -BaseUrl $BaseUrl
    }
    catch {
        $script:Errors += @{ section = "repositories"; error = $_.Exception.Message }
        return $null
    }
}

function Get-VeeamProxies {
    param([string]$Token, [string]$BaseUrl)

    try {
        return Get-VeeamPaginatedData -Endpoint "/api/v1/backupInfrastructure/proxies/states" -Token $Token -BaseUrl $BaseUrl
    }
    catch {
        $script:Errors += @{ section = "proxies"; error = $_.Exception.Message }
        return $null
    }
}

function Get-VeeamManagedServers {
    param([string]$Token, [string]$BaseUrl)

    try {
        return Get-VeeamPaginatedData -Endpoint "/api/v1/backupInfrastructure/managedServers" -Token $Token -BaseUrl $BaseUrl
    }
    catch {
        $script:Errors += @{ section = "managed_servers"; error = $_.Exception.Message }
        return $null
    }
}

function Get-VeeamLicense {
    param([string]$Token, [string]$BaseUrl)

    try {
        return Invoke-VeeamApi -Endpoint "/api/v1/license" -Token $Token -BaseUrl $BaseUrl
    }
    catch {
        $script:Errors += @{ section = "license"; error = $_.Exception.Message }
        return $null
    }
}

function Get-VeeamScaleoutRepositories {
    param([string]$Token, [string]$BaseUrl)

    try {
        return Get-VeeamPaginatedData -Endpoint "/api/v1/backupInfrastructure/scaleOutRepositories" -Token $Token -BaseUrl $BaseUrl
    }
    catch {
        $script:Errors += @{ section = "scaleout_repositories"; error = $_.Exception.Message }
        return $null
    }
}

function Get-VeeamWanAccelerators {
    param([string]$Token, [string]$BaseUrl)

    try {
        return Get-VeeamPaginatedData -Endpoint "/api/v1/backupInfrastructure/wanAccelerators" -Token $Token -BaseUrl $BaseUrl
    }
    catch {
        $script:Errors += @{ section = "wan_accelerators"; error = $_.Exception.Message }
        return $null
    }
}

# =============================================================================
# OUTPUT FUNCTIONS
# =============================================================================

function Write-AgentSection {
    <#
    .SYNOPSIS
        Output agent section in JSON format
    #>
    param(
        [string]$Name,
        [object]$Data
    )

    Write-Host "<<<veeam_rest_$($Name):sep(0)>>>"

    if ($null -eq $Data) {
        Write-Host "null"
    }
    elseif ($Data -is [array]) {
        # Convert array to JSON
        $json = $Data | ConvertTo-Json -Depth 10 -Compress
        if ($Data.Count -eq 0) {
            Write-Host "[]"
        }
        elseif ($Data.Count -eq 1) {
            # Single item arrays need special handling
            Write-Host "[$json]"
        }
        else {
            Write-Host $json
        }
    }
    else {
        # Single object
        Write-Host ($Data | ConvertTo-Json -Depth 10 -Compress)
    }
}

# =============================================================================
# MAIN
# =============================================================================

function Main {
    # Read configuration
    if (-not (Read-PluginConfig)) {
        # No config file - plugin disabled
        return
    }

    # Validate required settings
    if (-not $script:Config.username -or -not $script:Config.password) {
        return
    }

    # Disable SSL verification if configured
    Disable-SslVerification

    # Build base URL (always localhost)
    $baseUrl = "https://localhost:$($script:Config.port)"

    # Authenticate
    $token = Get-VeeamAuthToken -BaseUrl $baseUrl -Username $script:Config.username -Password $script:Config.password

    if (-not $token) {
        # Output authentication error section
        Write-Host "<<<veeam_rest_error>>>"
        Write-Host "Authentication failed"
        return
    }

    # Get server info for enrichment
    $serverName = $env:COMPUTERNAME
    if ($script:Config.sections -contains "server") {
        $serverInfo = Get-VeeamServerInfo -Token $token -BaseUrl $baseUrl
        if ($serverInfo) {
            $serverName = if ($serverInfo.backupServerName) { $serverInfo.backupServerName } else { $env:COMPUTERNAME }
            Write-AgentSection -Name "server" -Data $serverInfo
        }
    }
    else {
        # Try to get server name for enrichment even if not collecting server section
        try {
            $serverInfo = Invoke-VeeamApi -Endpoint "/api/v1/serverInfo" -Token $token -BaseUrl $baseUrl
            $serverName = if ($serverInfo.backupServerName) { $serverInfo.backupServerName } else { $env:COMPUTERNAME }
        }
        catch {
            # Use COMPUTERNAME as fallback
        }
    }

    # Calculate time filter for sessions/tasks
    $createdAfter = $null
    if ($script:Config.session_age -gt 0) {
        $createdAfter = [DateTime]::UtcNow.AddSeconds(-$script:Config.session_age).ToString("yyyy-MM-ddTHH:mm:ssZ")
    }

    # Collect and output sections
    if ($script:Config.sections -contains "jobs") {
        $jobs = Get-VeeamJobs -Token $token -BaseUrl $baseUrl -ServerName $serverName
        if ($null -ne $jobs) {
            Write-AgentSection -Name "jobs" -Data $jobs
        }
    }

    if ($script:Config.sections -contains "tasks") {
        $tasks = Get-VeeamTasks -Token $token -BaseUrl $baseUrl -ServerName $serverName -CreatedAfter $createdAfter
        if ($null -ne $tasks) {
            Write-AgentSection -Name "tasks" -Data $tasks
        }
    }

    if ($script:Config.sections -contains "sessions") {
        $sessions = Get-VeeamSessions -Token $token -BaseUrl $baseUrl -CreatedAfter $createdAfter
        if ($null -ne $sessions) {
            Write-AgentSection -Name "sessions" -Data $sessions
        }
    }

    if ($script:Config.sections -contains "repositories") {
        $repos = Get-VeeamRepositories -Token $token -BaseUrl $baseUrl
        if ($null -ne $repos) {
            Write-AgentSection -Name "repositories" -Data $repos
        }
    }

    if ($script:Config.sections -contains "proxies") {
        $proxies = Get-VeeamProxies -Token $token -BaseUrl $baseUrl
        if ($null -ne $proxies) {
            Write-AgentSection -Name "proxies" -Data $proxies
        }
    }

    if ($script:Config.sections -contains "managed_servers") {
        $servers = Get-VeeamManagedServers -Token $token -BaseUrl $baseUrl
        if ($null -ne $servers) {
            Write-AgentSection -Name "managed_servers" -Data $servers
        }
    }

    if ($script:Config.sections -contains "license") {
        $license = Get-VeeamLicense -Token $token -BaseUrl $baseUrl
        if ($null -ne $license) {
            Write-AgentSection -Name "license" -Data $license
        }
    }

    if ($script:Config.sections -contains "scaleout_repositories") {
        $scaleoutRepos = Get-VeeamScaleoutRepositories -Token $token -BaseUrl $baseUrl
        if ($null -ne $scaleoutRepos) {
            Write-AgentSection -Name "scaleout_repositories" -Data $scaleoutRepos
        }
    }

    if ($script:Config.sections -contains "wan_accelerators") {
        $wanAccelerators = Get-VeeamWanAccelerators -Token $token -BaseUrl $baseUrl
        if ($null -ne $wanAccelerators) {
            Write-AgentSection -Name "wan_accelerators" -Data $wanAccelerators
        }
    }

    # Output error section if any sections failed
    if ($script:Errors.Count -gt 0) {
        Write-AgentSection -Name "errors" -Data $script:Errors
    }
}

# Run main function
Main
