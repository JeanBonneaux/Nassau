# tcp_console.ps1 - console TCP du firmware roomba694_wifi (port 23), sans saisie interactive.
# Equivalent reseau de serial_console.ps1.
# Usage : .\tcp_console.ps1 -HostName 192.168.4.1 [-Port 23] [-Commands 's','b'] [-WaitAfter 1.5] [-InitialWait 1] [-ListenSeconds 0] [-Log fichier.txt]
#   -Commands      : touches envoyees une par une, chacune suivie d'un retour a la ligne, avec lecture de la reponse
#   -ListenSeconds : apres les commandes, continue d'ecouter pendant N secondes (ex. : -Commands 'j' -ListenSeconds 60 pour le CSV)
#   -Log           : ajoute tout ce qui est recu a ce fichier (UTF-8)
param(
  [string]$HostName = '192.168.4.1',
  [int]$Port = 23,
  [string[]]$Commands = @(),
  [double]$WaitAfter = 1.5,
  [double]$InitialWait = 1,
  [double]$ListenSeconds = 0,
  [string]$Log = ''
)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$utf8 = New-Object System.Text.UTF8Encoding($false)

$client = New-Object System.Net.Sockets.TcpClient
$client.NoDelay = $true
$client.Connect($HostName, $Port)
$stream = $client.GetStream()

function Read-All([double]$seconds) {
  $deadline = (Get-Date).AddSeconds($seconds)
  $ms = New-Object System.IO.MemoryStream
  $buf = New-Object byte[] 4096
  while ((Get-Date) -lt $deadline) {
    if ($stream.DataAvailable) {
      $n = $stream.Read($buf, 0, $buf.Length)
      if ($n -gt 0) { $ms.Write($buf, 0, $n) }
    } else {
      Start-Sleep -Milliseconds 30
    }
  }
  return $utf8.GetString($ms.ToArray())
}

function Emit([string]$text) {
  Write-Output $text
  if ($Log -ne '') { [System.IO.File]::AppendAllText($Log, $text + "`n", $utf8) }
}

try {
  Emit ("---- connecte a {0}:{1}, lecture {2} s ----" -f $HostName, $Port, $InitialWait)
  Emit (Read-All $InitialWait)
  foreach ($c in $Commands) {
    Emit ("---- envoi : '{0}' ----" -f $c)
    $bytes = $utf8.GetBytes($c + "`n")
    $stream.Write($bytes, 0, $bytes.Length)
    Emit (Read-All $WaitAfter)
  }
  if ($ListenSeconds -gt 0) {
    Emit ("---- ecoute pendant {0} s ----" -f $ListenSeconds)
    Emit (Read-All $ListenSeconds)
  }
} finally {
  $stream.Close()
  $client.Close()
}
