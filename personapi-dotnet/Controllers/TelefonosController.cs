using Microsoft.AspNetCore.Mvc;
using personapi_dotnet.Interfaces;
using personapi_dotnet.Models.Dtos;

namespace personapi_dotnet.Controllers;

public class TelefonosController : MvcControllerBase
{
    private readonly ITelefonoRepository _repository;
    private readonly IPersonaRepository _personas;

    public TelefonosController(ITelefonoRepository repository, IPersonaRepository personas)
    {
        _repository = repository;
        _personas = personas;

    }

    public async Task<IActionResult> Index()
    {
        var records = await _repository.GetAllAsync();
        await LoadLookups();
        return View(records);
    }

    public async Task<IActionResult> Details(string num)
    {
        if (string.IsNullOrWhiteSpace(num)) return BadRequest();
        var record = await _repository.GetByIdAsync(num);
        if (record == null) return NotFound();
        await LoadLookups();
        return View(TelefonoDto.FromEntity(record));
    }

    public async Task<IActionResult> Create()
    {
        await LoadLookups();
        return View(new TelefonoDto());
    }

    [HttpPost]
    public async Task<IActionResult> Create([Bind("Num,Oper,Duenio")] TelefonoDto model)
    {
        if (!await _personas.ExistsAsync(model.Duenio)) ModelState.AddModelError(nameof(model.Duenio), "Selecciona una persona existente.");
        if (ModelState.IsValid && await _repository.ExistsAsync(model.Num))
            ModelState.AddModelError("", "Ya existe un registro con ese identificador.");
        if (ModelState.IsValid && await SaveAsync(() => _repository.AddAsync(model.ToEntity())))
        {
            TempData["Success"] = "Registro creado correctamente.";
            return RedirectToAction(nameof(Index));
        }
        await LoadLookups();
        return View(model);
    }

    public async Task<IActionResult> Edit(string num)
    {
        if (string.IsNullOrWhiteSpace(num)) return BadRequest();
        var record = await _repository.GetByIdAsync(num);
        if (record == null) return NotFound();
        await LoadLookups();
        return View(TelefonoDto.FromEntity(record));
    }

    [HttpPost]
    public async Task<IActionResult> Edit([FromQuery(Name = "originalNum")] string num, [Bind("Num,Oper,Duenio")] TelefonoDto model)
    {
        if (string.IsNullOrWhiteSpace(num)) return BadRequest();
        if (num != model.Num) return BadRequest("No se puede modificar el identificador del registro.");
        if (!await _repository.ExistsAsync(num)) return NotFound();
        if (!await _personas.ExistsAsync(model.Duenio)) ModelState.AddModelError(nameof(model.Duenio), "Selecciona una persona existente.");
        if (ModelState.IsValid && await SaveAsync(() => _repository.UpdateAsync(model.ToEntity())))
        {
            TempData["Success"] = "Cambios guardados correctamente.";
            return RedirectToAction(nameof(Index));
        }
        await LoadLookups();
        return View(model);
    }

    public async Task<IActionResult> Delete(string num)
    {
        if (string.IsNullOrWhiteSpace(num)) return BadRequest();
        var record = await _repository.GetByIdAsync(num);
        if (record == null) return NotFound();
        await LoadLookups();
        return View(TelefonoDto.FromEntity(record));
    }

    [HttpPost, ActionName("Delete")]
    public async Task<IActionResult> DeleteConfirmed([FromQuery(Name = "originalNum")] string num)
    {
        if (string.IsNullOrWhiteSpace(num)) return BadRequest();
        var record = await _repository.GetByIdAsync(num);
        if (record == null) return NotFound();
        if (await SaveAsync(() => _repository.DeleteAsync(num)))
        {
            TempData["Success"] = "Registro eliminado correctamente.";
            return RedirectToAction(nameof(Index));
        }
        await LoadLookups();
        return View("Delete", TelefonoDto.FromEntity(record));
    }

    private async Task LoadLookups()
    {
        ViewBag.Personas = (await _personas.GetAllAsync()).ToDictionary(p => p.Cc, p => $"{p.Cc} · {p.Nombre} {p.Apellido}");

    }
}
