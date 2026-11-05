# Train the three 2026-11-04 consolidation candidates, one at a time (prepared 2026-11-04).
# The proven chain (RUNBOOK.md): bf16 LoRA on Qwen/Qwen2.5-3B-Instruct, 40 epochs, convert to
# GGUF, serve over the fp16 base tag (never q4), proof at temperature 0, then mark-trained.
# Activation stays a separate explicit operator action (Model-Lock-style).
#
# Hard rules honored here:
#   - NEVER run Ollama generations while training: every model is stopped first.
#   - BelowNormal priority so the desktop stays usable; checkpoints every 25 steps.
#   - One adapter at a time, strictly serial.
#
# Run from the training/ directory:  powershell -ExecutionPolicy Bypass -File train_consolidations.ps1

$ErrorActionPreference = "Stop"
$training = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $training
$py = Join-Path $training ".venv\Scripts\python.exe"
$log = Join-Path $training ("train_consolidations_{0:yyyyMMdd-HHmm}.log" -f (Get-Date))
$env:HF_HUB_OFFLINE = "1"   # base is in the local HF cache since August; no network needed
$env:HF_HUB_DISABLE_XET = "1"

$adapters = @(
    "adapter-omega-arc-house-20261105T025446",
    "adapter-omega-arc-runbooks-20261105T025647",
    "adapter-omega-arc-command-console-20261105T025822"
)

function Log([string]$msg) { $line = "[{0:HH:mm:ss}] {1}" -f (Get-Date), $msg; Write-Host $line; Add-Content -Path $log -Value $line -Encoding utf8 }

# ---- Stage 0: GPU exclusive — stop every loaded Ollama model (lesson of the v2 crash)
Log "stopping all loaded Ollama models"
$loaded = (& ollama ps) -split "`n" | Select-Object -Skip 1 | ForEach-Object { ($_ -split "\s+")[0] } | Where-Object { $_ }
foreach ($m in $loaded) { Log "  ollama stop $m"; & ollama stop $m }

# ---- Stage 1+2: train serially at BelowNormal (desktop stays usable)
$null = New-Item -ItemType Directory -Path (Join-Path $training "adapters") -Force
foreach ($id in $adapters) {
    $out = Join-Path $training "adapters\$id"
    if (Test-Path (Join-Path $out "adapter_model.safetensors")) { Log "$id already trained - skipping"; continue }
    Log "training $id (40 epochs, bf16, save every 25)"
    $p = Start-Process -FilePath $py -WorkingDirectory $training -NoNewWindow -PassThru `
        -ArgumentList @("train_adapter.py", "--data", "distillation\$id.jsonl", "--output", "adapters\$id", "--epochs", "40") `
        -RedirectStandardOutput "$out.train.log" -RedirectStandardError "$out.train.err"
    try { $p.PriorityClass = "BelowNormal" } catch {}
    $p.WaitForExit()
    if ($p.ExitCode -ne 0) { Log "TRAIN FAILED ($($p.ExitCode)) - see $out.train.err; stopping"; exit 1 }
    Log "$id trained"
}

# ---- Stage 3: convert each to GGUF, build model, proof, mark-trained
foreach ($id in $adapters) {
    $out = Join-Path $training "adapters\$id"
    $gguf = Join-Path $out "adapter.gguf"
    if (-not (Test-Path $gguf)) {
        Log "converting $id to GGUF"
        & $py "llama.cpp\convert_lora_to_gguf.py" $out --base "Qwen/Qwen2.5-3B-Instruct" --outfile $gguf
        if ($LASTEXITCODE -ne 0) { Log "CONVERT FAILED for $id; stopping"; exit 1 }
    }
    $short = ($id -replace '^adapter-omega-arc-','' -replace '^adapter-','' -replace '-\d{8}T\d{6}$','')
    $tag = "omega-arc-tutored-$short"
    $mf = Join-Path $out "Modelfile"
    # fp16 base, never q4: a bf16-trained LoRA loses its deltas over 4-bit weights (RUNBOOK rule 2)
    @(
        "FROM qwen2.5:3b-instruct-fp16",
        "ADAPTER ./adapter.gguf",
        "PARAMETER temperature 0",
        "SYSTEM You are 0M3-G4-ARC. Answer from your studied knowledge."
    ) | Set-Content $mf -Encoding ascii
    Log "ollama create $tag"
    & ollama create $tag -f $mf
    if ($LASTEXITCODE -ne 0) { Log "OLLAMA CREATE FAILED for $tag; stopping"; exit 1 }

    # proof: first 5 distilled questions, bare weights (no notes), answers logged for the operator
    Log "proof quiz for ${tag}:"
    $pairs = Get-Content "distillation\$id.jsonl" | Select-Object -First 5 | ForEach-Object { $_ | ConvertFrom-Json }
    foreach ($pair in $pairs) {
        $q = ($pair.messages | Where-Object role -eq "user").content
        $expected = ($pair.messages | Where-Object role -eq "assistant").content
        $body = @{ model = $tag; messages = @(@{ role = "user"; content = $q }); stream = $false } | ConvertTo-Json -Depth 5
        $resp = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:11434/api/chat" -ContentType "application/json" -Body $body -TimeoutSec 300
        $got = $resp.message.content
        Log ("  Q: {0}" -f $q)
        Log ("  expected: {0}" -f $expected)
        Log ("  got:      {0}" -f $got)
    }
    & ollama stop $tag 2>$null

    # registry: mark-trained (activation is NOT done here - explicit operator action)
    try {
        $null = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8001/system/tutelage/adapters/$id" -ContentType "application/json" -Body (@{ action = "mark-trained" } | ConvertTo-Json) -TimeoutSec 30
        Log "$id marked trained in the registry"
    } catch { Log "registry mark-trained failed for $id (backend down?) - do it manually: POST /system/tutelage/adapters/$id {action: mark-trained}" }
}
Log "all done - review the proof answers above, then activate per adapter when satisfied"
