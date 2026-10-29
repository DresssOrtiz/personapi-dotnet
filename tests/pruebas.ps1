param([string]$BaseUrl = "http://127.0.0.1:5025")
$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Net.Http
$handler = [System.Net.Http.HttpClientHandler]::new()
$handler.AllowAutoRedirect = $false
$handler.CookieContainer = [System.Net.CookieContainer]::new()
$client = [System.Net.Http.HttpClient]::new($handler)
$client.BaseAddress = [Uri]$BaseUrl
$client.Timeout = [TimeSpan]::FromSeconds(30)
$checks = 0
function Assert-True($Condition, [string]$Message) {
    if (!$Condition) { throw "FALLO: $Message" }
    $script:checks++
}
function Get-Page([string]$Path, [int]$Status = 200) {
    $response = $client.GetAsync($Path).GetAwaiter().GetResult()
    $html = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
    Assert-True ([int]$response.StatusCode -eq $Status) "GET $Path : $([int]$response.StatusCode), esperado $Status"
    return $html
}
function Post-Form([string]$Page, [string]$Target, [hashtable]$Data, [int]$Status = 302, [bool]$Token = $true) {
    $html = Get-Page $Page
    $form = [regex]::Match($html, '<form\b[^>]*action="([^"]+)"')
    Assert-True $form.Success "Formulario real en $Page"
    $actualTarget = [System.Net.WebUtility]::HtmlDecode($form.Groups[1].Value)
    Assert-True (!$actualTarget.StartsWith('/api/')) "Formulario apunta al controlador MVC en $Page"
    $actualUri = [Uri]::new($client.BaseAddress, $actualTarget)
    $expectedUri = [Uri]::new($client.BaseAddress, $Target)
    Assert-True ($actualUri.AbsolutePath -eq $expectedUri.AbsolutePath -and (($actualUri.Query.TrimStart('?').Split('&') | Sort-Object) -join '&') -eq (($expectedUri.Query.TrimStart('?').Split('&') | Sort-Object) -join '&')) "Acción y claves del formulario en $Page"
    $values = [System.Collections.Generic.Dictionary[string,string]]::new()
    foreach ($key in $Data.Keys) { $values[$key] = [string]$Data[$key] }
    if ($Token) {
        $match = [regex]::Match($html, 'name="__RequestVerificationToken"[^>]*value="([^"]+)"')
        Assert-True $match.Success "Token antifalsificación en $Page"
        $values["__RequestVerificationToken"] = [System.Net.WebUtility]::HtmlDecode($match.Groups[1].Value)
    }
    $content = [System.Net.Http.FormUrlEncodedContent]::new($values)
    $response = $client.PostAsync($actualTarget, $content).GetAwaiter().GetResult()
    $result = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
    Assert-True ([int]$response.StatusCode -eq $Status) "POST $Target : $([int]$response.StatusCode), esperado $Status"
    if ($Status -eq 302) {
        Assert-True ($response.Headers.Location.ToString() -match '^/(Personas|Telefonos|Profesiones|Estudios)(/Index)?$') "Redirección al listado en $Target"
    }
    return $result
}
$id = Get-Random -Minimum 1900000000 -Maximum 2000000000
$num = "399" + (Get-Random -Minimum 100000000 -Maximum 999999999)
$person = @{ Cc=$id; Nombre="Prueba MVC"; Apellido="Temporal"; Genero="F"; Edad="25" }
$profession = @{ Id=$id; Nom="Prueba MVC temporal"; Des="Registro de verificación" }
$phone = @{ Num=$num; Oper="Operador temporal"; Duenio=$id }
$study = @{ IdProf=$id; CcPer=$id; Fecha="2026-10-25"; Univer="Universidad de prueba" }
$created = [System.Collections.Generic.HashSet[string]]::new()
$baseline = @{}
try {
    foreach ($entity in @("personas","telefonos","profesiones","estudios")) { $baseline[$entity] = Get-Page "/api/$entity" }
    Get-Page "/api/personas/$id" 404 | Out-Null
    Get-Page "/api/profesiones/$id" 404 | Out-Null
    Get-Page "/api/telefonos/$num" 404 | Out-Null
    foreach ($path in @("/", "/Personas", "/Telefonos", "/Profesiones", "/Estudios", "/Personas/Create", "/Telefonos/Create", "/Profesiones/Create", "/Estudios/Create", "/swagger/index.html")) { Get-Page $path | Out-Null }
    $swagger = Get-Page "/swagger/v1/swagger.json" | ConvertFrom-Json
    Assert-True (@($swagger.paths.PSObject.Properties).Count -eq 8) "Swagger conserva las ocho rutas REST"

    Post-Form "/Personas/Create" "/Personas/Create" $person | Out-Null
    [void]$created.Add("Personas")
    Post-Form "/Profesiones/Create" "/Profesiones/Create" $profession | Out-Null
    [void]$created.Add("Profesiones")
    Post-Form "/Telefonos/Create" "/Telefonos/Create" $phone | Out-Null
    [void]$created.Add("Telefonos")
    Post-Form "/Estudios/Create" "/Estudios/Create" $study | Out-Null
    [void]$created.Add("Estudios")

    foreach ($entry in @(
        @("Personas","cc=$id"), @("Telefonos","num=$num"),
        @("Profesiones","id=$id"), @("Estudios","idProf=$id&ccPer=$id")
    )) {
        foreach ($action in @("Details","Edit","Delete")) { Get-Page "/$($entry[0])/$($action)?$($entry[1])" | Out-Null }
    }
    $readStudy = Get-Page "/api/estudios/$id/$id" | ConvertFrom-Json
    Assert-True ($readStudy.univer -eq $study.Univer) "Alta de estudios persistida"

    foreach ($entry in @(@("Personas",$person),@("Profesiones",$profession),@("Telefonos",$phone),@("Estudios",$study))) {
        $result = Post-Form "/$($entry[0])/Create" "/$($entry[0])/Create" $entry[1] 200
        Assert-True ($result -match 'Ya existe') "Duplicado controlado en $($entry[0])"
    }

    $invalid = @{ Cc=0; Nombre=""; Apellido=""; Genero="X"; Edad=-1 }
    $result = Post-Form "/Personas/Create" "/Personas/Create" $invalid 200
    Assert-True ($result -match 'validation-summary-errors') "Validaciones de persona en servidor"
    $invalidPhone = @{ Num=($num+"1"); Oper="Prueba"; Duenio=2147483647 }
    $result = Post-Form "/Telefonos/Create" "/Telefonos/Create" $invalidPhone 200
    Assert-True ($result -match 'Selecciona una persona existente') "FK de teléfono validada"
    $invalidStudy = @{ IdProf=2147483647; CcPer=2147483647; Fecha=""; Univer="" }
    $result = Post-Form "/Estudios/Create" "/Estudios/Create" $invalidStudy 200
    Assert-True ($result -match 'Selecciona una') "FK de estudios validada"

    Post-Form "/Personas/Create" "/Personas/Create" $person 400 $false | Out-Null
    $tampered = $person.Clone()
    $tampered.Cc = $id + 1
    Post-Form "/Personas/Edit?cc=$id" "/Personas/Edit?originalCc=$id" $tampered 400 | Out-Null

    $person.Nombre = "Prueba MVC editada"
    $person.Edad = ""
    $profession.Nom = "Profesión editada"
    $phone.Oper = "Operador editado"
    $study.Univer = "Universidad editada"
    $study.Fecha = ""
    Post-Form "/Personas/Edit?cc=$id" "/Personas/Edit?originalCc=$id" $person | Out-Null
    Post-Form "/Profesiones/Edit?id=$id" "/Profesiones/Edit?originalId=$id" $profession | Out-Null
    Post-Form "/Telefonos/Edit?num=$num" "/Telefonos/Edit?originalNum=$num" $phone | Out-Null
    Post-Form "/Estudios/Edit?idProf=$id&ccPer=$id" "/Estudios/Edit?originalIdProf=$id&originalCcPer=$id" $study | Out-Null
    $readPerson = Get-Page "/api/personas/$id" | ConvertFrom-Json
    Assert-True ($readPerson.nombre -eq $person.Nombre -and $null -eq $readPerson.edad) "Edición de persona y edad opcional"
    $personList = Get-Page "/Personas"
    $personRow = [regex]::Match($personList, '(?s)<tr>\s*<td>' + $id + '</td>.*?</tr>').Value
    $personCells = @([regex]::Matches($personRow, '(?s)<td[^>]*>(.*?)</td>') | ForEach-Object { [System.Net.WebUtility]::HtmlDecode($_.Groups[1].Value).Trim() })
    Assert-True ($personCells.Count -eq 6 -and $personCells[4] -eq '—') "Listado de personas muestra edad nula sin errores"
    Assert-True ((Get-Page "/api/profesiones/$id" | ConvertFrom-Json).nom -eq $profession.Nom) "Edición de profesión persistida"
    Assert-True ((Get-Page "/api/telefonos/$num" | ConvertFrom-Json).oper -eq $phone.Oper) "Edición de teléfono persistida"
    $readStudy = Get-Page "/api/estudios/$id/$id" | ConvertFrom-Json
    Assert-True ($readStudy.univer -eq $study.Univer -and $null -eq $readStudy.fecha) "Edición de estudio y fecha opcional"

    $result = Post-Form "/Personas/Delete?cc=$id" "/Personas/Delete?originalCc=$id" @{} 200
    Assert-True ($result -match 'registros relacionados') "Eliminación de persona con dependencias controlada"
    $result = Post-Form "/Profesiones/Delete?id=$id" "/Profesiones/Delete?originalId=$id" @{} 200
    Assert-True ($result -match 'registros relacionados') "Eliminación de profesión con dependencias controlada"
    Get-Page "/api/personas/$id" | Out-Null
    Get-Page "/api/profesiones/$id" | Out-Null

    foreach ($path in @('/RutaQueNoExiste/Accion', '/Home/AccionInexistente', '/Home/PageNotFound')) {
        $html = Get-Page $path 404
        Assert-True ($html -match 'sidebar' -and $html -match 'Volver al inicio') "404 con layout y regreso: $path"
    }
    foreach ($entry in @(@('Personas','cc=2147483647'), @('Profesiones','id=2147483647'), @('Telefonos','num=inexistente'), @('Estudios','idProf=2147483647&ccPer=2147483647'))) {
        foreach ($action in @('Details','Edit','Delete')) {
            $html = Get-Page "/$($entry[0])/$($action)?$($entry[1])" 404
            Assert-True ($html -match 'sidebar' -and $html -match 'Volver al inicio') "Registro inexistente con layout: $($entry[0])/$action"
        }
    }
    foreach ($path in @('/api/personas/2147483647', '/api/telefonos/inexistente', '/api/profesiones/2147483647', '/api/estudios/2147483647/2147483647', '/api/RutaQueNoExiste')) {
        $html = Get-Page $path 404
        Assert-True ($html -notmatch 'sidebar|Volver al inicio') "La API no recibe la vista MVC: $path"
    }
    $html = Get-Page '/Personas/Details?cc=0' 400
    Assert-True ($html -notmatch 'Volver al inicio') 'El error 400 MVC conserva su comportamiento'
    foreach ($module in @('Personas','Profesiones')) {
        $html = Get-Page "/$module/Create"
        Assert-True ($html -notmatch 'class="validation-summary-errors"') "Sin recuadro de error inicial: $module"
        Assert-True ($html -match 'class="validation-summary-valid"') "Resumen disponible para validación cliente: $module"
        $key = if ($module -eq 'Personas') { 'Cc' } else { 'Id' }
        $keyInput = [regex]::Match($html, "<input\b[^>]*name=" + '"' + $key + '"' + "[^>]*>").Value
        Assert-True ($keyInput -match 'value=""') "La clave inicial permanece vacía: $module"
        $result = Post-Form "/$module/Create" "/$module/Create" @{ $key='0'; Nombre=''; Nom='' } 200
        Assert-True ($result -match 'class="validation-summary-errors"' -and $result -match 'obligatorio') "El resumen contiene errores reales: $module"
    }
    $people = Get-Page '/api/personas' | ConvertFrom-Json
    $list = Get-Page '/Personas'
    Assert-True ($list -match '<th scope="col">Edad</th>') 'Columna Edad presente'
    foreach ($row in $people) {
        $match = [regex]::Match($list, '(?s)<tr>\s*<td>' + $row.cc + '</td>.*?</tr>').Value
        $cells = @([regex]::Matches($match, '(?s)<td[^>]*>(.*?)</td>') | ForEach-Object { [System.Net.WebUtility]::HtmlDecode($_.Groups[1].Value).Trim() })
        $expected = if ($null -eq $row.edad) { '—' } else { [string]$row.edad }
        Assert-True ($cells.Count -eq 6 -and $cells[4] -eq $expected) "Edad correcta para persona $($row.cc)"
    }
}
finally {
    foreach ($entry in @(
        @("Estudios","idProf=$id&ccPer=$id","originalIdProf=$id&originalCcPer=$id","/api/estudios/$id/$id"),
        @("Telefonos","num=$num","originalNum=$num","/api/telefonos/$num"),
        @("Profesiones","id=$id","originalId=$id","/api/profesiones/$id"),
        @("Personas","cc=$id","originalCc=$id","/api/personas/$id")
    )) {
        if ($created.Contains($entry[0])) {
            Post-Form "/$($entry[0])/Delete?$($entry[1])" "/$($entry[0])/Delete?$($entry[2])" @{} | Out-Null
            Get-Page $entry[3] 404 | Out-Null
        }
    }
    foreach ($entity in $baseline.Keys) {
        Assert-True ((Get-Page "/api/$entity") -eq $baseline[$entity]) "Datos iniciales conservados: $entity"
    }
    $client.Dispose()
    $handler.Dispose()
}
Write-Output "CORRECTO: $checks comprobaciones HTTP. CRUD de las cuatro entidades, validación, CSRF, duplicados, relaciones, páginas 404, columna Edad y limpieza de datos."
