# Offline Russian voices for the recovered CCTV recording.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$projectRoot = Split-Path -Parent $PSScriptRoot
$definitionPath = Join-Path $projectRoot 'resources/puzzles/cctv/archive.json'
$definition = Get-Content -LiteralPath $definitionPath -Raw -Encoding UTF8 | ConvertFrom-Json
$audioDirectory = Join-Path $projectRoot 'resources/audio/cctv/voices'
New-Item -ItemType Directory -Force -Path $audioDirectory | Out-Null
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $synth.SelectVoice('Microsoft Irina Desktop')
    $index = 0
    foreach ($line in $definition.recording) {
        if (-not $line.speaker) { continue }
        $index++
        $name = 'recording_{0:00}.wav' -f $index
        $format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(44100, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
        $synth.SetOutputToWaveFile((Join-Path $audioDirectory $name), $format)
        $pitch = if ($line.speaker -eq 'archive_friend') { '+7%' } else { '-7%' }
        $rate = if ($line.speaker -eq 'archive_friend') { '-2%' } else { '+2%' }
        $escaped = [System.Security.SecurityElement]::Escape($line.text)
        $ssml = '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="ru-RU"><prosody pitch="{0}" rate="{1}">{2}</prosody></speak>' -f $pitch,$rate,$escaped
        $synth.SpeakSsml($ssml)
        $synth.SetOutputToNull()
        Write-Output $name
    }
} finally { $synth.Dispose() }
& (Join-Path $projectRoot '.venv/Scripts/python.exe') (Join-Path $PSScriptRoot 'time_campaign_voices.py')
if ($LASTEXITCODE -ne 0) { throw 'Voice timing update failed.' }
