# Measure the nav rail label widths in WPF units, so the label for the new page can
# be chosen from a measurement instead of a guess. The rail button is 68 wide with
# 12 of margin each side and 2 of padding inside the label, so the text has 64 DIP
# to fit in - and a label that overflows is silently replaced by an ellipsis.

Add-Type -AssemblyName PresentationCore, PresentationFramework, WindowsBase

$visual = New-Object System.Windows.Media.DrawingVisual
$dpi = [System.Windows.Media.VisualTreeHelper]::GetDpi($visual)
$pixelsPerDip = $dpi.PixelsPerDip

# The rail labels use whatever the theme picks, so measure both candidates.
$families = @('Bahnschrift SemiBold', 'Bahnschrift', 'Segoe UI')

$candidates = @(
    'Studio',
    'Luma Studio',
    'LumaStudio',
    'Luma Studio ',
    'Studio Luma'
)

Write-Output ('  available width inside the label: {0} DIP' -f 64)
Write-Output ''

foreach ($family in $families) {
    $typeface = New-Object System.Windows.Media.Typeface($family)
    if (-not $typeface.FontFamily.FamilyNames.ContainsKey([System.Windows.Markup.XmlLanguage]::GetLanguage('en-US'))) { }
    foreach ($text in $candidates) {
        $formatted = New-Object System.Windows.Media.FormattedText(
            $text,
            [System.Globalization.CultureInfo]::InvariantCulture,
            [System.Windows.FlowDirection]::LeftToRight,
            $typeface,
            9,
            [System.Windows.Media.Brushes]::White,
            $pixelsPerDip)
        $fits = if ($formatted.Width -le 64) { 'fits' } else { 'CLIPPED' }
        Write-Output ('  {0,-20} {1,-14} {2,7:N2} DIP  {3}' -f $family, $text, $formatted.Width, $fits)
    }
    Write-Output ''
}
