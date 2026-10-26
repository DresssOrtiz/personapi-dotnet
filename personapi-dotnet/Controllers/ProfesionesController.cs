using Microsoft.AspNetCore.Mvc;
using personapi_dotnet.Interfaces;
using personapi_dotnet.Models.Dtos;

namespace personapi_dotnet.Controllers;

public class ProfesionesController : MvcControllerBase
{
    private readonly IProfesionRepository _repository;

    public ProfesionesController(IProfesionRepository repository)
    {
        _repository = repository;


    }

    public async Task<IActionResult> Index()
    {
        var records = await _repository.GetAllAsync();
        await LoadLookups();
        return View(records);
    }

    public async Task<IActionResult> Details(int id)
    {
        if (id <= 0) return BadRequest();
        var record = await _repository.GetByIdAsync(id);
        if (record == null) return NotFound();
        await LoadLookups();
        return View(ProfesionDto.FromEntity(record));
    }

    public async Task<IActionResult> Create()
    {
        await LoadLookups();
        ModelState.SetModelValue(nameof(ProfesionDto.Id), "", "");
        return View(new ProfesionDto());
    }

    [HttpPost]
    public async Task<IActionResult> Create([Bind("Id,Nom,Des")] ProfesionDto model)
    {

        if (ModelState.IsValid && await _repository.ExistsAsync(model.Id))
            ModelState.AddModelError("", "Ya existe un registro con ese identificador.");
        if (ModelState.IsValid && await SaveAsync(() => _repository.AddAsync(model.ToEntity())))
        {
            TempData["Success"] = "Registro creado correctamente.";
            return RedirectToAction(nameof(Index));
        }
        await LoadLookups();
        return View(model);
    }

    public async Task<IActionResult> Edit(int id)
    {
        if (id <= 0) return BadRequest();
        var record = await _repository.GetByIdAsync(id);
        if (record == null) return NotFound();
        await LoadLookups();
        return View(ProfesionDto.FromEntity(record));
    }

    [HttpPost]
    public async Task<IActionResult> Edit([FromQuery(Name = "originalId")] int id, [Bind("Id,Nom,Des")] ProfesionDto model)
    {
        if (id <= 0) return BadRequest();
        if (id != model.Id) return BadRequest("No se puede modificar el identificador del registro.");
        if (!await _repository.ExistsAsync(id)) return NotFound();

        if (ModelState.IsValid && await SaveAsync(() => _repository.UpdateAsync(model.ToEntity())))
        {
            TempData["Success"] = "Cambios guardados correctamente.";
            return RedirectToAction(nameof(Index));
        }
        await LoadLookups();
        return View(model);
    }

    public async Task<IActionResult> Delete(int id)
    {
        if (id <= 0) return BadRequest();
        var record = await _repository.GetByIdAsync(id);
        if (record == null) return NotFound();
        await LoadLookups();
        return View(ProfesionDto.FromEntity(record));
    }

    [HttpPost, ActionName("Delete")]
    public async Task<IActionResult> DeleteConfirmed([FromQuery(Name = "originalId")] int id)
    {
        if (id <= 0) return BadRequest();
        var record = await _repository.GetByIdAsync(id);
        if (record == null) return NotFound();
        if (await SaveAsync(() => _repository.DeleteAsync(id)))
        {
            TempData["Success"] = "Registro eliminado correctamente.";
            return RedirectToAction(nameof(Index));
        }
        await LoadLookups();
        return View("Delete", ProfesionDto.FromEntity(record));
    }

    private async Task LoadLookups()
    {
        await Task.CompletedTask;
    }
}
