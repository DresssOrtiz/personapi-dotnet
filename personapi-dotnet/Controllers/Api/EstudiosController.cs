using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using personapi_dotnet.Interfaces;
using personapi_dotnet.Models.Dtos;

namespace personapi_dotnet.Controllers.Api
{
    [ApiController]
    [Route("api/estudios")]
    [Produces("application/json")]
    public class EstudiosController : ControllerBase
    {
        private readonly IEstudioRepository _estudios;
        private readonly IPersonaRepository _personas;
        private readonly IProfesionRepository _profesiones;

        public EstudiosController(
            IEstudioRepository estudios,
            IPersonaRepository personas,
            IProfesionRepository profesiones)
        {
            _estudios = estudios;
            _personas = personas;
            _profesiones = profesiones;
        }

        [HttpGet]
        [ProducesResponseType(typeof(IEnumerable<EstudioDto>), StatusCodes.Status200OK)]
        public async Task<ActionResult<IEnumerable<EstudioDto>>> GetAll()
        {
            var estudios = await _estudios.GetAllAsync();
            return Ok(estudios.Select(EstudioDto.FromEntity));
        }

        [HttpGet("{idProf:int}/{ccPer:int}")]
        [ProducesResponseType(typeof(EstudioDto), StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        public async Task<ActionResult<EstudioDto>> GetById(int idProf, int ccPer)
        {
            var estudio = await _estudios.GetByIdAsync(idProf, ccPer);
            if (estudio == null) return NotFound();
            return Ok(EstudioDto.FromEntity(estudio));
        }

        [HttpPost]
        [ProducesResponseType(typeof(EstudioDto), StatusCodes.Status201Created)]
        [ProducesResponseType(StatusCodes.Status400BadRequest)]
        [ProducesResponseType(StatusCodes.Status409Conflict)]
        public async Task<ActionResult<EstudioDto>> Create(EstudioDto dto)
        {
            var error = await ValidateReferencesAsync(dto);
            if (error != null) return BadRequest(error);
            var conflict = new ProblemDetails
            {
                Title = $"Ya existe un estudio para la profesion {dto.IdProf} y la persona {dto.CcPer}."
            };
            if (await _estudios.ExistsAsync(dto.IdProf, dto.CcPer))
                return Conflict(conflict);

            try
            {
                await _estudios.AddAsync(dto.ToEntity());
            }
            catch (DbUpdateException ex) when (ex.IsDuplicateKey())
            {
                return Conflict(conflict);
            }
            return CreatedAtAction(nameof(GetById), new { idProf = dto.IdProf, ccPer = dto.CcPer }, dto);
        }

        [HttpPut("{idProf:int}/{ccPer:int}")]
        [ProducesResponseType(StatusCodes.Status204NoContent)]
        [ProducesResponseType(StatusCodes.Status400BadRequest)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        public async Task<IActionResult> Update(int idProf, int ccPer, EstudioDto dto)
        {
            if (idProf != dto.IdProf || ccPer != dto.CcPer)
                return BadRequest(new ProblemDetails { Title = "La clave de la ruta no coincide con la del cuerpo." });
            if (!await _estudios.ExistsAsync(idProf, ccPer)) return NotFound();

            await _estudios.UpdateAsync(dto.ToEntity());
            return NoContent();
        }

        [HttpDelete("{idProf:int}/{ccPer:int}")]
        [ProducesResponseType(StatusCodes.Status204NoContent)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        public async Task<IActionResult> Delete(int idProf, int ccPer)
        {
            if (!await _estudios.ExistsAsync(idProf, ccPer)) return NotFound();

            await _estudios.DeleteAsync(idProf, ccPer);
            return NoContent();
        }

        private async Task<ProblemDetails?> ValidateReferencesAsync(EstudioDto dto)
        {
            if (!await _profesiones.ExistsAsync(dto.IdProf))
                return new ProblemDetails { Title = $"No existe una profesion con id {dto.IdProf}." };
            if (!await _personas.ExistsAsync(dto.CcPer))
                return new ProblemDetails { Title = $"No existe una persona con cc {dto.CcPer}." };
            return null;
        }
    }
}
