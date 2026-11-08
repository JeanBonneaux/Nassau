# serial_console.ps1 - pilote le moniteur serie du sketch roomba694_test1 sans saisie interactive.
# Usage : .\serial_console.ps1 -Port COM3 [-Reset] [-Commands '?','w','s','b'] [-WaitAfter 1.5] [-InitialWait 3]
#   -Reset    : reset materiel de l'ESP32 via la ligne RTS (comme esptool : DTR bas, RTS haut 100 ms puis bas)
#   -Commands : touches envoyees une par une, chacune suivie d'un retour a la ligne, avec lecture de la reponse
param(
  [Parameter(Mandatory=$true)][string]$Port,
  [string[]]$Commands = @(),
  [double]$WaitAfter = 1.5,
  [double]$InitialWait = 3,
  [switch]$Reset,
  [int]$Baud = 115200
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$sp = New-Object System.IO.Ports.SerialPort $Port, $Baud, 'None', 8, 'One'
$sp.ReadTimeout = 200
$sp.DtrEnable = $false
$sp.RtsEnable = $false
$sp.Open()

function Read-All([double]$seconds) {
  $deadline = (Get-Date).AddSeconds($seconds)
  $ms = New-Object System.IO.MemoryStream
  $buf = New-Object byte[] 4096
  while ((Get-Date) -lt $deadline) {
    $n = $sp.BytesToRead
    if ($n -gt 0) {
      if ($n -gt $buf.Length) { $n = $buf.Length }
      $r = $sp.Read($buf, 0, $n)
      $ms.Write($buf, 0, $r)
    } else {
      Start-Sleep -Milliseconds 30
    }
  }
  return [System.Text.Encoding]::UTF8.GetString($ms.ToArray())
}

try {
  if ($Reset) {
    $sp.DtrEnable = $false
    $sp.RtsEnable = $true
    Start-Sleep -Milliseconds 100
    $sp.RtsEnable = $false
  }
  Write-Output ("---- sortie apres ouverture du port ({0} s) ----" -f $InitialWait)
  Write-Output (Read-All $InitialWait)
  foreach ($c in $Commands) {
    Write-Output ("---- envoi : '{0}' ----" -f $c)
    $sp.Write($c + "`n")
    Write-Output (Read-All $WaitAfter)
  }
} finally {
  $sp.Close()
}
