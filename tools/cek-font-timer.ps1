# Which timer fonts does GDI+ actually resolve?
#
# The styles name "Segoe UI Variable Display Light", which is a VARIABLE font.
# GDI+ (System.Drawing) has poor support for variable fonts: naming a variable
# instance often fails to resolve and silently falls back to plain "Segoe UI".
# That is exactly what "the font still looks basic" means.
#
# This lists what is installed and, for each candidate, whether GDI+ resolves
# the exact name. Pure ASCII.

Add-Type -AssemblyName System.Drawing

Write-Output "--- installed families matching the candidates ---"
$patterns = @('Segoe UI*', 'Inter*', 'SF Pro*', 'SFPro*', 'Helvetica*', 'Roboto*', 'Lato*', 'Open Sans*', 'Source Sans*', 'Nunito*', 'Montserrat*', 'Poppins*', 'Arial*', 'Bahnschrift*', 'Corbel*', 'Candara*', 'Franklin*', 'DIN*', 'Manrope*', 'Rubik*', 'Outfit*', 'Urbanist*', 'Plus Jakarta*')

$families = [System.Drawing.FontFamily]::Families
$found = @()
foreach ($f in $families) {
    foreach ($p in $patterns) {
        if ($f.Name -like $p) { $found += $f.Name; break }
    }
}
foreach ($n in ($found | Sort-Object -Unique)) {
    $fam = New-Object System.Drawing.FontFamily($n)
    $styles = @()
    if ($fam.IsStyleAvailable([System.Drawing.FontStyle]::Regular)) { $styles += 'Regular' }
    if ($fam.IsStyleAvailable([System.Drawing.FontStyle]::Bold)) { $styles += 'Bold' }
    if ($fam.IsStyleAvailable([System.Drawing.FontStyle]::Italic)) { $styles += 'Italic' }
    Write-Output ("  {0,-44} {1}" -f $n, ($styles -join ','))
}

Write-Output ""
Write-Output "--- does GDI+ resolve the exact thin names the timer asks for? ---"
$names = @(
    'Segoe UI Variable Display Light',
    'Segoe UI Variable Display',
    'Segoe UI Variable Display Semilight',
    'Segoe UI Variable Text Light',
    'Segoe UI Light',
    'Segoe UI Semilight',
    'Segoe UI'
)
foreach ($n in $names) {
    $ok = $false
    $resolved = '?'
    try {
        $fam = New-Object System.Drawing.FontFamily($n)
        $ok = $true
        $resolved = $fam.Name
    } catch {
        $ok = $false
        $resolved = 'THROWS'
    }
    # A name that resolves to a DIFFERENT family name is a silent fallback.
    $exact = 'no'
    if ($resolved -eq $n) { $exact = 'EXACT' }
    Write-Output ("  {0,-42} ok={1,-6} resolved={2,-42} {3}" -f $n, $ok, $resolved, $exact)
}

Write-Output ""
Write-Output "--- measured width of '10:09' at 96px in each candidate ---"
$bmp = New-Object System.Drawing.Bitmap(400, 160)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
foreach ($n in @('Segoe UI Variable Display Light','Segoe UI Light','Segoe UI','Inter','Arial')) {
    try {
        $fam = New-Object System.Drawing.FontFamily($n)
        $f = New-Object System.Drawing.Font($fam, 96, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
        $sz = $g.MeasureString('10:09', $f)
        Write-Output ("  {0,-42} {1,7:N1} x {2,6:N1}" -f $fam.Name, $sz.Width, $sz.Height)
        $f.Dispose()
    } catch {
        Write-Output ("  {0,-42} unavailable" -f $n)
    }
}
$g.Dispose()
$bmp.Dispose()
