# Offline Russian memory voices. Reads the authored JSON, never requires network.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$projectRoot = Split-Path -Parent $PSScriptRoot
$dialoguePath = Join-Path $projectRoot 'resources/story/hospital/acts/act0/dialogue.json'
$dialogues = Get-Content -LiteralPath $dialoguePath -Raw -Encoding UTF8 | ConvertFrom-Json
$audioDirectory = Join-Path $projectRoot 'resources/audio/act0'
New-Item -ItemType Directory -Force -Path $audioDirectory | Out-Null
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $synth.SelectVoice('Microsoft Irina Desktop')
    foreach ($group in @('cradle_memory','memory_outro_first','memory_outro_second')) {
        $index = 0
        foreach ($line in $dialogues.$group) {
            $index++
            $name = '{0}_{1:00}.wav' -f $group, $index
            $path = Join-Path $audioDirectory $name
            $format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(44100, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
            $synth.SetOutputToWaveFile($path,$format)
            $pitch = if ($line.speaker -eq 'child') { '+18%' } elseif ($line.speaker -eq 'mother') { '-10%' } else { '-3%' }
            $rate = if ($line.speaker -eq 'child') { '+7%' } elseif ($line.speaker -eq 'mother') { '-4%' } else { '-14%' }
            $escaped = [System.Security.SecurityElement]::Escape($line.text)
            $ssml = '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="ru-RU"><prosody pitch="{0}" rate="{1}">{2}</prosody></speak>' -f $pitch,$rate,$escaped
            $synth.SpeakSsml($ssml)
            $synth.SetOutputToNull()
            Write-Output $name
        }
    }
} finally { $synth.Dispose() }
# Persist measured timings and file paths; the game does not need Windows TTS.
$python = Join-Path $projectRoot '.venv/Scripts/python.exe'
& $python (Join-Path $PSScriptRoot 'time_spotlights_voices.py')
if ($LASTEXITCODE -ne 0) { throw 'Voice timing update failed.' }
