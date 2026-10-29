using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using personapi_dotnet.Interfaces;
using personapi_dotnet.Models.Dtos;

namespace personapi_dotnet.Controllers.Api
{
    [ApiController]
    [Route("api/profesiones")]
    [Produces("application/json")]
    public class ProfesionesController : ControllerBase
    {
        private readonly IProfesionRepository _profesiones;

        public ProfesionesController(IProfesionRepository profesiones)
        {
            _profesiones = profesiones;
        }

        /// <summary>Lista todas las profesiones.</summary>
        [HttpGet]
        [ProducesResponseType(typeof(IEnumerable<ProfesionDto>), StatusCodes.Status200OK)]
        public async Task<ActionResult<IEnumerable<ProfesionDto>>> GetAll()
        {
            var profesiones = await _profesiones.GetAllAsync();
            return Ok(profesiones.Select(ProfesionDto.FromEntity));
        }

        /// <summary>Obtiene una profesion por su identificador.</summary>
        /// <param name="id">Identificador de la profesion.</param>
        [HttpGet("{id:int}")]
        [ProducesResponseType(typeof(ProfesionDto), StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        public async Task<ActionResult<ProfesionDto>> GetById(int id)
        {
            var profesion = await _profesiones.GetByIdAsync(id);
            if (profesion == null) return NotFound();
            return Ok(ProfesionDto.FromEntity(profesion));
        }

        /// <summary>Crea una profesion. Responde 409 si ya existe una con el mismo identificador.</summary>
        /// <param name="dto">Datos de la profesion a crear.</param>
        [HttpPost]
        [ProducesResponseType(typeof(ProfesionDto), StatusCodes.Status201Created)]
        [ProducesResponseType(StatusCodes.Status400BadRequest)]
        [ProducesResponseType(StatusCodes.Status409Conflict)]
        public async Task<ActionResult<ProfesionDto>> Create(ProfesionDto dto)
        {
            var conflict = new ProblemDetails { Title = $"Ya existe una profesion con id {dto.Id}." };
            if (await _profesiones.ExistsAsync(dto.Id))
                return Conflict(conflict);

            try
            {
                await _profesiones.AddAsync(dto.ToEntity());
            }
            catch (DbUpdateException ex) when (ex.IsDuplicateKey())
            {
                return Conflict(conflict);
            }
            return CreatedAtAction(nameof(GetById), new { id = dto.Id }, dto);
        }

        /// <summary>Actualiza una profesion existente.</summary>
        /// <param name="id">Identificador de la profesion; debe coincidir con el del cuerpo.</param>
        /// <param name="dto">Nuevos datos de la profesion.</param>
        [HttpPut("{id:int}")]
        [ProducesResponseType(StatusCodes.Status204NoContent)]
        [ProducesResponseType(StatusCodes.Status400BadRequest)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        public async Task<IActionResult> Update(int id, ProfesionDto dto)
        {
            if (id != dto.Id)
                return BadRequest(new ProblemDetails { Title = "El id de la ruta no coincide con el del cuerpo." });
            if (!await _profesiones.ExistsAsync(id)) return NotFound();

            await _profesiones.UpdateAsync(dto.ToEntity());
            return NoContent();
        }

        /// <summary>Elimina una profesion. Responde 409 si tiene estudios asociados.</summary>
        /// <param name="id">Identificador de la profesion.</param>
        [HttpDelete("{id:int}")]
        [ProducesResponseType(StatusCodes.Status204NoContent)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        [ProducesResponseType(StatusCodes.Status409Conflict)]
        public async Task<IActionResult> Delete(int id)
        {
            if (!await _profesiones.ExistsAsync(id)) return NotFound();

            try
            {
                await _profesiones.DeleteAsync(id);
            }
            catch (DbUpdateException)
            {
                return Conflict(new ProblemDetails
                {
                    Title = "No se puede eliminar la profesion porque tiene estudios asociados."
                });
            }
            return NoContent();
        }
    }
}
