# Bedient een VirtualBox-VM van buitenaf: toetsenbord, muis, schermafdruk, en een bestand in de gast
# lezen. Gemaakt om een labo als student door te lopen en de figuren van een opdracht opnieuw te maken
# (eerst gebruikt voor de ProCurve-opdracht van DeN, 29 september 2026).
#
#   vm.ps1 shot <pad.png> [term|x,y,w,h]   schermafdruk; 'term' snijdt het zwarte terminalvlak uit
#   vm.ps1 type "<tekst>"                  typt tekst
#   vm.ps1 line "<tekst>"                  typt tekst en ENTER
#   vm.ps1 key "enter space ctrl-c"        speciale toetsen, gescheiden door spaties (ook up, down, shift-tab)
#   vm.ps1 click <x> <y> [right|double]    muisklik op schermcoordinaten van de schermafdruk
#   vm.ps1 drag <x1,y1> <x2,y2>            slepen met de linkerknop ingedrukt (een module in Packet Tracer)
#   vm.ps1 scroll <x> <y> <n>              muiswiel op x,y: n positief scrolt omlaag, negatief omhoog
#   vm.ps1 move <x> <y>                    muis verplaatsen zonder klik (een tooltip laten verschijnen)
#   vm.ps1 run "<bash-commando>"           voert een commando uit in de gast (guestcontrol)
#   vm.ps1 tail <bestand> [n]              laatste n regels van een bestand in de gast, zonder escapecodes
#   vm.ps1 scherm <putty-log> [rijen] [kol] de regels die de terminal nu toont, afgespeeld uit het log
#
# De VM en de gebruiker komen uit ORION_VM (standaard Ubuntu), ORION_VM_USER en ORION_VM_PASSWORD. Het
# wachtwoord staat bewust niet in deze repo: die is publiek.
#
# Het toetsenbord van de gast moet Belgian azerty zijn. keyboardputstring van VBoxManage typt als
# qwerty, dus deze module stuurt scancodes met een azerty-tabel. ~ is een dode toets en heeft geen code.
param([string]$cmd, [string]$a1, [string]$a2, [string]$a3)

$ErrorActionPreference = 'Stop'
$VM = if ($env:ORION_VM) { $env:ORION_VM } else { 'Ubuntu' }
$VBM = Join-Path $env:ProgramFiles 'Oracle\VirtualBox\VBoxManage.exe'

function Gast {
    if (-not $env:ORION_VM_USER -or -not $env:ORION_VM_PASSWORD) {
        throw 'Zet ORION_VM_USER en ORION_VM_PASSWORD voor commando''s in de gast.'
    }
    return @('--username', $env:ORION_VM_USER, '--password', $env:ORION_VM_PASSWORD)
}

# Scancodes (set 1). Een PowerShell-hashtable is hoofdletterongevoelig, en dan overschrijft 'T' de 't':
# vandaar de ordinale vergelijking.
$map = New-Object System.Collections.Hashtable ([StringComparer]::Ordinal)
function M($chars, $code, $mod) { foreach ($c in $chars.ToCharArray()) { $map[[string]$c] = @($code, $mod) } }
$letters = @{ a=0x10; z=0x11; e=0x12; r=0x13; t=0x14; y=0x15; u=0x16; i=0x17; o=0x18; p=0x19
              q=0x1E; s=0x1F; d=0x20; f=0x21; g=0x22; h=0x23; j=0x24; k=0x25; l=0x26; m=0x27
              w=0x2C; x=0x2D; c=0x2E; v=0x2F; b=0x30; n=0x31 }
foreach ($k in $letters.Keys) { $map[$k] = @($letters[$k], ''); $map[$k.ToUpper()] = @($letters[$k], 's') }
$rij = @(@('&','1',0x02), @([string][char]0xE9,'2',0x03), @('"','3',0x04), @("'",'4',0x05), @('(','5',0x06),
         @([string][char]0xA7,'6',0x07), @([string][char]0xE8,'7',0x08), @('!','8',0x09), @([string][char]0xE7,'9',0x0A),
         @([string][char]0xE0,'0',0x0B), @(')',[string][char]0xB0,0x0C), @('-','_',0x0D))
foreach ($r in $rij) { $map[$r[0]] = @($r[2], ''); $map[$r[1]] = @($r[2], 's') }
M '$' 0x1B ''; M '*' 0x1B 's'; M ([string][char]0xF9) 0x28 ''; M '%' 0x28 's'
M ',' 0x32 ''; M '?' 0x32 's'; M ';' 0x33 ''; M '.' 0x33 's'; M ':' 0x34 ''; M '/' 0x34 's'
M '=' 0x35 ''; M '+' 0x35 's'; M '<' 0x56 ''; M '>' 0x56 's'; M ' ' 0x39 ''
M '|' 0x02 'g'; M '@' 0x03 'g'; M '#' 0x04 'g'; M '{' 0x0A 'g'; M '}' 0x0B 'g'
M '[' 0x1A 'g'; M ']' 0x1B 'g'; M '\' 0x56 'g'
$speciaal = @{ enter=0x1C; esc=0x01; tab=0x0F; backspace=0x0E; space=0x39; caps=0x3A }
# Toetsen met het voorvoegsel E0; super opent het overzicht van GNOME, waar een geminimaliseerd venster terugkomt.
# Ook up en down: zonder E0 zijn het de pijltjes van het numeriek klavier, en een Flutter-lijst (het
# installatieprogramma van Ubuntu 26.04) reageert daar niet op.
$uitgebreid = @{ super=0x5B; up=0x48; down=0x50; left=0x4B; right=0x4D; delete=0x53; home=0x47; end=0x4F; pgup=0x49; pgdn=0x51 }

function Stuur([int[]]$codes) {
    # VBoxManage neemt een beperkt aantal codes per aanroep
    for ($i = 0; $i -lt $codes.Count; $i += 48) {
        $stuk = $codes[$i..([Math]::Min($i + 47, $codes.Count - 1))] | ForEach-Object { '{0:x2}' -f $_ }
        & $VBM controlvm $VM keyboardputscancode @stuk | Out-Null
        Start-Sleep -Milliseconds 60
    }
}
function Codes([string]$tekst) {
    $uit = New-Object System.Collections.Generic.List[int]
    foreach ($ch in $tekst.ToCharArray()) {
        $e = $map[[string]$ch]
        if (-not $e) { throw "Geen scancode voor '$ch'" }
        $code, $mod = $e
        if ($mod -eq 's') { $uit.Add(0x2A) }
        if ($mod -eq 'g') { $uit.Add(0xE0); $uit.Add(0x38) }
        $uit.Add($code); $uit.Add($code -bor 0x80)
        if ($mod -eq 's') { $uit.Add(0xAA) }
        if ($mod -eq 'g') { $uit.Add(0xE0); $uit.Add(0xB8) }
    }
    return ,$uit.ToArray()
}

# Zoekt het terminalvlak: de grootste rechthoek van zuiver zwarte achtergrond (PuTTY, 0,0,0). Een rij hoort
# erbij als ze een lange zwarte reeks bevat; tekst breekt een rij, maar de lege pixelrijen tussen twee
# tekstregels niet. Boven 40 px (GNOME-balk) en links van 70 px (dock) wordt niet gezocht.
Add-Type -AssemblyName System.Drawing
Add-Type -ReferencedAssemblies System.Drawing.Common, System.Drawing.Primitives, System.Runtime.InteropServices -TypeDefinition @'
using System; using System.Drawing; using System.Drawing.Imaging; using System.Runtime.InteropServices;
public static class Terminal {
    public static int[] Zoek(Bitmap bmp) {
        var d = bmp.LockBits(new Rectangle(0, 0, bmp.Width, bmp.Height), ImageLockMode.ReadOnly, PixelFormat.Format24bppRgb);
        var buf = new byte[d.Stride * bmp.Height]; Marshal.Copy(d.Scan0, buf, 0, buf.Length); bmp.UnlockBits(d);
        Func<int,int,bool> zwart = (x, y) => { int i = y * d.Stride + x * 3; return buf[i] < 8 && buf[i+1] < 8 && buf[i+2] < 8; };
        int top = -1, bot = -1, left = bmp.Width, right = 0;
        for (int y = 40; y < bmp.Height; y++) {
            int run = 0, best = 0, bs = 0, s = 0;
            for (int x = 70; x < bmp.Width; x++) {
                if (zwart(x, y)) { if (run == 0) s = x; run++; if (run > best) { best = run; bs = s; } } else run = 0;
            }
            if (best >= 300) {
                if (top < 0) top = y; bot = y;
                if (bs < left) left = bs; if (bs + best - 1 > right) right = bs + best - 1;
            }
        }
        if (top < 0) return null;
        return new int[] { left, top, right - left + 1, bot - top + 1 };
    }

    // Speelt een PuTTY-sessielog af op een scherm van rows x cols, zoals een VT100 het zou tonen, en
    // geeft de regels terug. Genoeg voor wat een switch stuurt: cursorpositie, regel wissen, ESC E,
    // scrollen en automatisch afbreken; kleuren en modi worden genegeerd.
    public static string[] Speel(byte[] data, int rows, int cols) {
        var g = new char[rows, cols];
        for (int r = 0; r < rows; r++) for (int c = 0; c < cols; c++) g[r, c] = ' ';
        int cr = 0, cc = 0;
        Action lf = () => {
            if (cr < rows - 1) { cr++; return; }
            for (int r = 1; r < rows; r++) for (int c = 0; c < cols; c++) g[r - 1, c] = g[r, c];
            for (int c = 0; c < cols; c++) g[rows - 1, c] = ' ';
        };
        for (int i = 0; i < data.Length; i++) {
            char ch = (char)data[i];
            if (ch == 27 && i + 1 < data.Length) {
                char n = (char)data[i + 1];
                if (n == '[') {
                    int j = i + 2; var p = new System.Text.StringBuilder();
                    while (j < data.Length && !char.IsLetter((char)data[j])) { p.Append((char)data[j]); j++; }
                    if (j >= data.Length) break;
                    char f = (char)data[j]; i = j;
                    string ps = p.ToString().TrimStart('?');
                    string[] a = ps.Split(';');
                    Func<int, int, int> arg = (k, d) => { int v; return (k < a.Length && int.TryParse(a[k], out v) && v > 0) ? v : d; };
                    if (f == 'H' || f == 'f') { cr = Math.Min(rows - 1, arg(0, 1) - 1); cc = Math.Min(cols - 1, arg(1, 1) - 1); }
                    else if (f == 'K') {
                        int m = ps.Length == 0 ? 0 : arg(0, 0);
                        int from = m == 0 ? cc : 0, to = m == 1 ? cc : cols - 1;
                        for (int c = from; c <= to; c++) g[cr, c] = ' ';
                    }
                    else if (f == 'J' && ps == "2") { for (int r = 0; r < rows; r++) for (int c = 0; c < cols; c++) g[r, c] = ' '; }
                    else if (f == 'A') cr = Math.Max(0, cr - arg(0, 1));
                    else if (f == 'B') cr = Math.Min(rows - 1, cr + arg(0, 1));
                    else if (f == 'C') cc = Math.Min(cols - 1, cc + arg(0, 1));
                    else if (f == 'D') cc = Math.Max(0, cc - arg(0, 1));
                    continue;
                }
                i++;
                if (n == 'E') { cc = 0; lf(); } else if (n == 'D') lf();
                continue;
            }
            if (ch == '\r') { cc = 0; continue; }
            if (ch == '\n') { lf(); continue; }
            if (ch == '\b') { if (cc > 0) cc--; continue; }
            if (ch == '\t') { cc = Math.Min(cols - 1, (cc / 8 + 1) * 8); continue; }
            if (ch < 32) continue;
            if (cc >= cols) { cc = 0; lf(); }
            g[cr, cc] = ch; cc++;
        }
        var uit = new string[rows];
        for (int r = 0; r < rows; r++) { var b = new char[cols]; for (int c = 0; c < cols; c++) b[c] = g[r, c]; uit[r] = new string(b).TrimEnd(); }
        return uit;
    }
}
'@

switch ($cmd) {
    'shot' {
        $pad = [IO.Path]::GetFullPath($a1)
        New-Item -ItemType Directory -Force (Split-Path $pad) | Out-Null
        & $VBM controlvm $VM screenshotpng $pad
        if ($a2) {
            $img = [System.Drawing.Bitmap]::FromFile($pad)
            $r = if ($a2 -eq 'term') { [Terminal]::Zoek($img) } else { $a2.Split(',') | ForEach-Object { [int]$_ } }
            if (-not $r) { $img.Dispose(); throw 'Geen terminalvlak gevonden' }
            $rect = New-Object System.Drawing.Rectangle $r[0], $r[1], $r[2], $r[3]
            $uit = $img.Clone($rect, $img.PixelFormat); $img.Dispose()
            $uit.Save($pad, [System.Drawing.Imaging.ImageFormat]::Png); $uit.Dispose()
        }
        $pad
    }
    'type' { Stuur (Codes $a1) }
    'line' { Stuur ((Codes $a1) + @(0x1C, 0x9C)) }
    'key' {
        foreach ($k in $a1.Split(' ')) {
            if ($k -match '^ctrl-(.)$') { $c = $letters[$Matches[1]]; Stuur @(0x1D, $c, ($c -bor 0x80), 0x9D) }
            elseif ($k -eq 'shift-tab') { Stuur @(0x2A, 0x0F, 0x8F, 0xAA) }
            elseif ($speciaal.ContainsKey($k)) { $c = $speciaal[$k]; Stuur @($c, ($c -bor 0x80)) }
            elseif ($uitgebreid.ContainsKey($k)) { $c = $uitgebreid[$k]; Stuur @(0xE0, $c, 0xE0, ($c -bor 0x80)) }
            else { throw "Onbekende toets $k" }
        }
    }
    'click' {
        $vbox = New-Object -ComObject VirtualBox.VirtualBox
        $s = New-Object -ComObject VirtualBox.Session
        $vbox.FindMachine($VM).LockMachine($s, 1)
        try {
            $m = $s.Console.Mouse; $x = [int]$a1; $y = [int]$a2
            $knop = if ($a3 -eq 'right') { 2 } else { 1 }
            $m.PutMouseEventAbsolute($x, $y, 0, 0, 0); Start-Sleep -Milliseconds 100
            $n = if ($a3 -eq 'double') { 2 } else { 1 }
            for ($i = 0; $i -lt $n; $i++) {
                $m.PutMouseEventAbsolute($x, $y, 0, 0, $knop); Start-Sleep -Milliseconds 60
                $m.PutMouseEventAbsolute($x, $y, 0, 0, 0); Start-Sleep -Milliseconds 80
            }
        } finally { $s.UnlockMachine() }
    }
    { $_ -in 'drag', 'scroll', 'move' } {
        $vbox = New-Object -ComObject VirtualBox.VirtualBox
        $s = New-Object -ComObject VirtualBox.Session
        $vbox.FindMachine($VM).LockMachine($s, 1)
        try {
            $m = $s.Console.Mouse
            if ($cmd -eq 'drag') {
                # Tussenstappen, want een programma dat pas bij beweging een sleepactie start (Qt) ziet
                # een sprong van begin naar eind niet als slepen.
                $van = $a1 -split ',' | ForEach-Object { [int]$_ }; $naar = $a2 -split ',' | ForEach-Object { [int]$_ }
                $m.PutMouseEventAbsolute($van[0], $van[1], 0, 0, 0); Start-Sleep -Milliseconds 150
                $m.PutMouseEventAbsolute($van[0], $van[1], 0, 0, 1); Start-Sleep -Milliseconds 600
                for ($i = 1; $i -le 40; $i++) {
                    $x = $van[0] + ($naar[0] - $van[0]) * $i / 40; $y = $van[1] + ($naar[1] - $van[1]) * $i / 40
                    $m.PutMouseEventAbsolute([int]$x, [int]$y, 0, 0, 1); Start-Sleep -Milliseconds 60
                }
                Start-Sleep -Milliseconds 800
                $m.PutMouseEventAbsolute($naar[0], $naar[1], 0, 0, 0)
            } elseif ($cmd -eq 'scroll') {
                $m.PutMouseEventAbsolute([int]$a1, [int]$a2, 0, 0, 0); Start-Sleep -Milliseconds 100
                $n = [int]$a3; $stap = [Math]::Sign($n)
                for ($i = 0; $i -lt [Math]::Abs($n); $i++) {
                    $m.PutMouseEventAbsolute([int]$a1, [int]$a2, $stap, 0, 0); Start-Sleep -Milliseconds 60
                }
            } else {
                $m.PutMouseEventAbsolute([int]$a1, [int]$a2, 0, 0, 0)
            }
        } finally { $s.UnlockMachine() }
    }
    'run' { & $VBM guestcontrol $VM run @(Gast) --exe /bin/bash -- -c $a1 }
    'scherm' {
        # het scherm zoals een terminal van 80x24 het nu toont, afgespeeld uit een PuTTY-sessielog in de gast
        $b64 = (& $VBM guestcontrol $VM run @(Gast) --exe /bin/bash -- -c "base64 -w0 '$a1'") -join ''
        $rij = if ($a2) { [int]$a2 } else { 24 }; $kol = if ($a3) { [int]$a3 } else { 80 }
        [Terminal]::Speel([Convert]::FromBase64String($b64), $rij, $kol)
    }
    'tail' {
        $n = if ($a2) { $a2 } else { '60' }
        & $VBM guestcontrol $VM run @(Gast) --exe /bin/bash -- -c "sed -e 's/\x1b\[[0-9;?]*[A-Za-z]//g' -e 's/\x1b.//g' -e 's/\r//g' '$a1' | tail -n $n"
    }
    default { throw "Onbekend commando '$cmd'. Zie de kop van dit bestand." }
}
