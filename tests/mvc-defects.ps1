param([string]$BaseUrl = "http://127.0.0.1:5035")
$ErrorActionPreference = "Stop"
$handler = [System.Net.Http.HttpClientHandler]::new()
$handler.AllowAutoRedirect = $false
$handler.CookieContainer = [System.Net.CookieContainer]::new()
$client = [System.Net.Http.HttpClient]::new($handler)
$client.BaseAddress = [Uri]$BaseUrl
$checks = 0
function Check($condition, [string]$message) {
    if (!$condition) { throw "FALLO: $message" }
    $script:checks++
}
function Read-Page([string]$path, [int]$status = 200) {
    $response = $client.GetAsync($path).GetAwaiter().GetResult()
    Check ([int]$response.StatusCode -eq $status) "GET $path debe devolver $status"
    return $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
}
try {
    foreach ($path in @('/RutaQueNoExiste/Accion', '/Home/AccionInexistente', '/Home/PageNotFound')) {
        $html = Read-Page $path 404
        Check ($html -match 'sidebar' -and $html -match 'Volver al inicio') "404 con layout y regreso: $path"
    }
    foreach ($entry in @(@('Personas','cc=2147483647'), @('Profesiones','id=2147483647'), @('Telefonos','num=QA-inexistente'), @('Estudios','idProf=2147483647&ccPer=2147483647'))) {
        foreach ($action in @('Details','Edit','Delete')) {
            $html = Read-Page "/$($entry[0])/$($action)?$($entry[1])" 404
            Check ($html -match 'sidebar' -and $html -match 'Volver al inicio') "Registro inexistente con layout: $($entry[0])/$action"
        }
    }
    foreach ($path in @('/api/personas/2147483647', '/api/telefonos/QA-inexistente', '/api/profesiones/2147483647', '/api/estudios/2147483647/2147483647', '/api/RutaQueNoExiste')) {
        $html = Read-Page $path 404
        Check ($html -notmatch 'sidebar|Volver al inicio') "La API no recibe la vista MVC: $path"
    }
    $html = Read-Page '/Personas/Details?cc=0' 400
    Check ($html -notmatch 'Volver al inicio') 'El error 400 MVC conserva su comportamiento'
    foreach ($module in @('Personas','Profesiones')) {
        $html = Read-Page "/$module/Create"
        Check ($html -notmatch 'class="validation-summary-errors"') "Sin recuadro de error inicial: $module"
        Check ($html -match 'class="validation-summary-valid"') "Resumen disponible para validación cliente: $module"
        $key = if ($module -eq 'Personas') { 'Cc' } else { 'Id' }
        $input = [regex]::Match($html, "<input\b[^>]*name=" + '"' + $key + '"' + "[^>]*>").Value
        Check ($input -match 'value=""') "La clave inicial permanece vacía: $module"
        $token = [regex]::Match($html, 'name="__RequestVerificationToken"[^>]*value="([^"]+)"').Groups[1].Value
        $values = [System.Collections.Generic.Dictionary[string,string]]::new()
        $values['__RequestVerificationToken'] = [System.Net.WebUtility]::HtmlDecode($token)
        $values[$key] = '0'
        $values['Nombre'] = ''
        $values['Nom'] = ''
        $content = [System.Net.Http.FormUrlEncodedContent]::new($values)
        $response = $client.PostAsync("/$module/Create", $content).GetAwaiter().GetResult()
        $invalid = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
        Check ([int]$response.StatusCode -eq 200) "El POST inválido vuelve al formulario: $module"
        Check ($invalid -match 'class="validation-summary-errors"' -and $invalid -match 'obligatorio') "El resumen contiene errores reales: $module"
    }
    $people = Read-Page '/api/personas' | ConvertFrom-Json
    $list = Read-Page '/Personas'
    Check ($list -match '<th scope="col">Edad</th>') 'Columna Edad presente'
    foreach ($person in $people) {
        $row = [regex]::Match($list, '(?s)<tr>\s*<td>' + $person.cc + '</td>.*?</tr>').Value
        $cells = @([regex]::Matches($row, '(?s)<td[^>]*>(.*?)</td>') | ForEach-Object { [System.Net.WebUtility]::HtmlDecode($_.Groups[1].Value).Trim() })
        $expected = if ($null -eq $person.edad) { '—' } else { [string]$person.edad }
        Check ($cells.Count -eq 6 -and $cells[4] -eq $expected) "Edad correcta para persona $($person.cc)"
    }
    Write-Output "CORRECTO: $checks comprobaciones de DEF-06, DEF-07 y DEF-09."
}
finally {
    $client.Dispose()
    $handler.Dispose()
}
