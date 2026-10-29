using Microsoft.AspNetCore.Mvc;
using personapi_dotnet.Interfaces;
using personapi_dotnet.Models.Dtos;

namespace personapi_dotnet.Controllers;

public class PersonasController : MvcControllerBase
{
    private readonly IPersonaRepository _repository;

    public PersonasController(IPersonaRepository repository)
    {
        _repository = repository;


    }

    public async Task<IActionResult> Index()
    {
        var records = await _repository.GetAllAsync();
        await LoadLookups();
        return View(records);
    }

    public async Task<IActionResult> Details(int cc)
    {
        if (cc <= 0) return BadRequest();
        var record = await _repository.GetByIdAsync(cc);
        if (record == null) return NotFound();
        await LoadLookups();
        return View(PersonaDto.FromEntity(record));
    }

    public async Task<IActionResult> Create()
    {
        await LoadLookups();
        ModelState.SetModelValue(nameof(PersonaDto.Cc), "", "");
        ModelState.MarkFieldValid(nameof(PersonaDto.Cc));
        return View(new PersonaDto());
    }

    [HttpPost]
    public async Task<IActionResult> Create([Bind("Cc,Nombre,Apellido,Genero,Edad")] PersonaDto model)
    {

        if (ModelState.IsValid && await _repository.ExistsAsync(model.Cc))
            ModelState.AddModelError("", "Ya existe un registro con ese identificador.");
        if (ModelState.IsValid && await SaveAsync(() => _repository.AddAsync(model.ToEntity())))
        {
            TempData["Success"] = "Registro creado correctamente.";
            return RedirectToAction(nameof(Index));
        }
        await LoadLookups();
        return View(model);
    }

    public async Task<IActionResult> Edit(int cc)
    {
        if (cc <= 0) return BadRequest();
        var record = await _repository.GetByIdAsync(cc);
        if (record == null) return NotFound();
        await LoadLookups();
        return View(PersonaDto.FromEntity(record));
    }

    [HttpPost]
    public async Task<IActionResult> Edit([FromQuery(Name = "originalCc")] int cc, [Bind("Cc,Nombre,Apellido,Genero,Edad")] PersonaDto model)
    {
        if (cc <= 0) return BadRequest();
        if (cc != model.Cc) return BadRequest("No se puede modificar el identificador del registro.");
        if (!await _repository.ExistsAsync(cc)) return NotFound();

        if (ModelState.IsValid && await SaveAsync(() => _repository.UpdateAsync(model.ToEntity())))
        {
            TempData["Success"] = "Cambios guardados correctamente.";
            return RedirectToAction(nameof(Index));
        }
        await LoadLookups();
        return View(model);
    }

    public async Task<IActionResult> Delete(int cc)
    {
        if (cc <= 0) return BadRequest();
        var record = await _repository.GetByIdAsync(cc);
        if (record == null) return NotFound();
        await LoadLookups();
        return View(PersonaDto.FromEntity(record));
    }

    [HttpPost, ActionName("Delete")]
    public async Task<IActionResult> DeleteConfirmed([FromQuery(Name = "originalCc")] int cc)
    {
        if (cc <= 0) return BadRequest();
        var record = await _repository.GetByIdAsync(cc);
        if (record == null) return NotFound();
        if (await SaveAsync(() => _repository.DeleteAsync(cc)))
        {
            TempData["Success"] = "Registro eliminado correctamente.";
            return RedirectToAction(nameof(Index));
        }
        await LoadLookups();
        return View("Delete", PersonaDto.FromEntity(record));
    }

    private async Task LoadLookups()
    {
        await Task.CompletedTask;
    }
}
