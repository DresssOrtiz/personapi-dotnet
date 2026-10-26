using Microsoft.AspNetCore.Mvc;
using personapi_dotnet.Interfaces;
using personapi_dotnet.Models.Dtos;

namespace personapi_dotnet.Controllers;

public class EstudiosController : MvcControllerBase
{
    private readonly IEstudioRepository _repository;
    private readonly IPersonaRepository _personas;
private readonly IProfesionRepository _profesiones;

    public EstudiosController(IEstudioRepository repository, IPersonaRepository personas, IProfesionRepository profesiones)
    {
        _repository = repository;
        _personas = personas;
        _profesiones = profesiones;
    }

    public async Task<IActionResult> Index()
    {
        var records = await _repository.GetAllAsync();
        await LoadLookups();
        return View(records);
    }

    public async Task<IActionResult> Details(int idProf, int ccPer)
    {
        if (idProf <= 0 || ccPer <= 0) return BadRequest();
        var record = await _repository.GetByIdAsync(idProf, ccPer);
        if (record == null) return NotFound();
        await LoadLookups();
        return View(EstudioDto.FromEntity(record));
    }

    public async Task<IActionResult> Create()
    {
        await LoadLookups();
        return View(new EstudioDto());
    }

    [HttpPost]
    public async Task<IActionResult> Create([Bind("IdProf,CcPer,Fecha,Univer")] EstudioDto model)
    {
        if (!await _personas.ExistsAsync(model.CcPer)) ModelState.AddModelError(nameof(model.CcPer), "Selecciona una persona existente.");
        if (!await _profesiones.ExistsAsync(model.IdProf)) ModelState.AddModelError(nameof(model.IdProf), "Selecciona una profesión existente.");
        if (ModelState.IsValid && await _repository.ExistsAsync(model.IdProf, model.CcPer))
            ModelState.AddModelError("", "Ya existe un registro con ese identificador.");
        if (ModelState.IsValid && await SaveAsync(() => _repository.AddAsync(model.ToEntity())))
        {
            TempData["Success"] = "Registro creado correctamente.";
            return RedirectToAction(nameof(Index));
        }
        await LoadLookups();
        return View(model);
    }

    public async Task<IActionResult> Edit(int idProf, int ccPer)
    {
        if (idProf <= 0 || ccPer <= 0) return BadRequest();
        var record = await _repository.GetByIdAsync(idProf, ccPer);
        if (record == null) return NotFound();
        await LoadLookups();
        return View(EstudioDto.FromEntity(record));
    }

    [HttpPost]
    public async Task<IActionResult> Edit([FromQuery(Name = "originalIdProf")] int idProf, [FromQuery(Name = "originalCcPer")] int ccPer, [Bind("IdProf,CcPer,Fecha,Univer")] EstudioDto model)
    {
        if (idProf <= 0 || ccPer <= 0) return BadRequest();
        if (idProf != model.IdProf || ccPer != model.CcPer) return BadRequest("No se puede modificar el identificador del registro.");
        if (!await _repository.ExistsAsync(idProf, ccPer)) return NotFound();
        if (!await _personas.ExistsAsync(model.CcPer)) ModelState.AddModelError(nameof(model.CcPer), "Selecciona una persona existente.");
        if (!await _profesiones.ExistsAsync(model.IdProf)) ModelState.AddModelError(nameof(model.IdProf), "Selecciona una profesión existente.");
        if (ModelState.IsValid && await SaveAsync(() => _repository.UpdateAsync(model.ToEntity())))
        {
            TempData["Success"] = "Cambios guardados correctamente.";
            return RedirectToAction(nameof(Index));
        }
        await LoadLookups();
        return View(model);
    }

    public async Task<IActionResult> Delete(int idProf, int ccPer)
    {
        if (idProf <= 0 || ccPer <= 0) return BadRequest();
        var record = await _repository.GetByIdAsync(idProf, ccPer);
        if (record == null) return NotFound();
        await LoadLookups();
        return View(EstudioDto.FromEntity(record));
    }

    [HttpPost, ActionName("Delete")]
    public async Task<IActionResult> DeleteConfirmed([FromQuery(Name = "originalIdProf")] int idProf, [FromQuery(Name = "originalCcPer")] int ccPer)
    {
        if (idProf <= 0 || ccPer <= 0) return BadRequest();
        var record = await _repository.GetByIdAsync(idProf, ccPer);
        if (record == null) return NotFound();
        if (await SaveAsync(() => _repository.DeleteAsync(idProf, ccPer)))
        {
            TempData["Success"] = "Registro eliminado correctamente.";
            return RedirectToAction(nameof(Index));
        }
        await LoadLookups();
        return View("Delete", EstudioDto.FromEntity(record));
    }

    private async Task LoadLookups()
    {
        ViewBag.Personas = (await _personas.GetAllAsync()).ToDictionary(p => p.Cc, p => $"{p.Cc} · {p.Nombre} {p.Apellido}");
ViewBag.Profesiones = (await _profesiones.GetAllAsync()).ToDictionary(p => p.Id, p => p.Nom);

    }
}
