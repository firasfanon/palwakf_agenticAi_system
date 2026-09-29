$ErrorActionPreference = 'Stop'
$svc = Get-Service -Name PalWakfOutboundLocalExecutorV1 -ErrorAction Stop
[pscustomobject]@{
  ServiceName = $svc.Name
  Status = $svc.Status.ToString()
  StartType = $svc.StartType.ToString()
  ConfigSet = -not [string]::IsNullOrWhiteSpace([Environment]::GetEnvironmentVariable('PALWAKF_EXECUTOR_CONFIG','Machine'))
}
