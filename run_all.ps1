<#
  run_all.ps1 — прогнать весь словарь Турабаева на Windows.
  OCR'ит 6 частей (по 104 стр.) параллельными процессами, затем мёржит в один JSON.

  Перед запуском:
    1) tesseract и poppler (pdftoppm) должны быть в PATH
    2) папка tessdata с rus/kaz/uzb_cyrl .traineddata
    3) pip install pypdf

  Запуск (из папки репозитория):
    powershell -ExecutionPolicy Bypass -File run_all.ps1 `
        -Pdf "D:\My projects\dictionaries\turabaev\Turabaev...slovar.pdf" `
        -Tessdata "D:\tools\tessdata" -Dpi 300
#>
param(
    [Parameter(Mandatory=$true)][string]$Pdf,
    [Parameter(Mandatory=$true)][string]$Tessdata,
    [int]$Dpi = 300,
    [string]$Out = ".\out"
)

$env:TESSDATA_PREFIX = $Tessdata
New-Item -ItemType Directory -Force -Path $Out | Out-Null

# 6 частей по 104 страницы (622 всего)
$ranges = @(
    @{first=1;   last=104},
    @{first=105; last=208},
    @{first=209; last=312},
    @{first=313; last=416},
    @{first=417; last=520},
    @{first=521; last=622}
)

$jobs = @()
foreach ($r in $ranges) {
    $partOut = Join-Path $Out ("part_{0:000}-{1:000}" -f $r.first, $r.last)
    Write-Host "Starting part $($r.first)-$($r.last) -> $partOut"
    $jobs += Start-Job -ScriptBlock {
        param($pdf,$po,$f,$l,$dpi,$td)
        $env:TESSDATA_PREFIX = $td
        python turabaev_pipeline.py "$pdf" --out "$po" --first $f --last $l --dpi $dpi --batch 52
    } -ArgumentList $Pdf,$partOut,$r.first,$r.last,$Dpi,$Tessdata
}

Write-Host "Running $($jobs.Count) parts in parallel. Waiting..."
$jobs | Wait-Job | Receive-Job
$jobs | Remove-Job

Write-Host "Merging all parts..."
python merge_batches.py "$Out" -o (Join-Path $Out "turabaev_merged.json")
Write-Host "Done. Result: $(Join-Path $Out 'turabaev_merged.json')"
