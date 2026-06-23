<#
  run_all.ps1 — прогнать весь словарь Турабаева на Windows.
  OCR'ит части параллельными процессами, затем мёржит в один JSON.

  Перед запуском:
    1) tesseract и poppler (pdftoppm) должны быть в PATH
    2) папка tessdata с rus/kaz/uzb_cyrl .traineddata
    3) pip install pypdf

  Два режима:
    -Pdf <файл>       — один цельный PDF, бьётся на 6 частей по 104 стр. (622 всего)
    -PartsDir <папка> — папка с уже разбитыми частями, имена вида
                         turabaev_partNN_pAAA-BBB.pdf (смещение страниц берётся из BBB/AAA)

  Запуск:
    powershell -ExecutionPolicy Bypass -File run_all.ps1 `
        -PartsDir "D:\My projects\dictionaries\turabaev" -Tessdata ".\tessdata" -Dpi 300
#>
param(
    [string]$Pdf,
    [string]$PartsDir,
    [Parameter(Mandatory=$true)][string]$Tessdata,
    [int]$Dpi = 300,
    [string]$Out = ".\out"
)

if (-not $Pdf -and -not $PartsDir) { throw "Specify either -Pdf or -PartsDir" }

$env:TESSDATA_PREFIX = $Tessdata
# winget's poppler install updates the User PATH registry value, but PowerShell sessions
# started before that update keep a stale in-memory PATH (and so do their Start-Job children) —
# prepend it explicitly so pdftoppm resolves regardless of session age.
$popplerBin = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages\oschwartz10612.Poppler*\poppler-*\Library\bin" -Directory -ErrorAction SilentlyContinue | Select-Object -First 1
if ($popplerBin -and ($env:Path -notlike "*$($popplerBin.FullName)*")) { $env:Path = "$($popplerBin.FullName);$env:Path" }
New-Item -ItemType Directory -Force -Path $Out | Out-Null
$Out = (Resolve-Path $Out).Path
# Start-Job runspaces default to the user's Documents folder, not the caller's CWD —
# use absolute script paths so jobs find turabaev_pipeline.py regardless.
$pipelineScript = Join-Path $PSScriptRoot "turabaev_pipeline.py"
$mergeScript = Join-Path $PSScriptRoot "merge_batches.py"

$jobs = @()

if ($PartsDir) {
    $parts = Get-ChildItem -Path $PartsDir -Filter "turabaev_part*_p*.pdf" | Sort-Object Name
    if (-not $parts) { throw "No turabaev_part*_p*.pdf files found in $PartsDir" }
    foreach ($p in $parts) {
        if ($p.Name -notmatch '_p(\d+)-(\d+)\.pdf$') { throw "Can't parse page range from $($p.Name)" }
        $offset = [int]$Matches[1] - 1
        $partOut = Join-Path $Out ("part_{0:000}-{1:000}" -f ([int]$Matches[1]), ([int]$Matches[2]))
        Write-Host "Starting $($p.Name) (offset $offset) -> $partOut"
        $jobs += Start-Job -ScriptBlock {
            param($pdf,$po,$dpi,$td,$off,$script)
            $env:TESSDATA_PREFIX = $td
            python "$script" "$pdf" --out "$po" --dpi $dpi --batch 52 --page-offset $off
        } -ArgumentList $p.FullName,$partOut,$Dpi,$Tessdata,$offset,$pipelineScript
    }
} else {
    # 6 частей по 104 страницы (622 всего) из одного цельного PDF
    $ranges = @(
        @{first=1;   last=104},
        @{first=105; last=208},
        @{first=209; last=312},
        @{first=313; last=416},
        @{first=417; last=520},
        @{first=521; last=622}
    )
    foreach ($r in $ranges) {
        $partOut = Join-Path $Out ("part_{0:000}-{1:000}" -f $r.first, $r.last)
        Write-Host "Starting part $($r.first)-$($r.last) -> $partOut"
        $jobs += Start-Job -ScriptBlock {
            param($pdf,$po,$f,$l,$dpi,$td,$script)
            $env:TESSDATA_PREFIX = $td
            python "$script" "$pdf" --out "$po" --first $f --last $l --dpi $dpi --batch 52
        } -ArgumentList $Pdf,$partOut,$r.first,$r.last,$Dpi,$Tessdata,$pipelineScript
    }
}

Write-Host "Running $($jobs.Count) parts in parallel. Waiting..."
$jobs | Wait-Job | Receive-Job
$jobs | Remove-Job

Write-Host "Merging all parts..."
python "$mergeScript" "$Out" -o (Join-Path $Out "turabaev_merged.json")
Write-Host "Done. Result: $(Join-Path $Out 'turabaev_merged.json')"
