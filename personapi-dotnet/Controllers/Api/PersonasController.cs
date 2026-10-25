using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using personapi_dotnet.Interfaces;
using personapi_dotnet.Models.Dtos;

namespace personapi_dotnet.Controllers.Api
{
    [ApiController]
    [Route("api/personas")]
    [Produces("application/json")]
    public class PersonasController : ControllerBase
    {
        private readonly IPersonaRepository _personas;

        public PersonasController(IPersonaRepository personas)
        {
            _personas = personas;
        }

        [HttpGet]
        [ProducesResponseType(typeof(IEnumerable<PersonaDto>), StatusCodes.Status200OK)]
        public async Task<ActionResult<IEnumerable<PersonaDto>>> GetAll()
        {
            var personas = await _personas.GetAllAsync();
            return Ok(personas.Select(PersonaDto.FromEntity));
        }

        [HttpGet("{cc:int}")]
        [ProducesResponseType(typeof(PersonaDto), StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        public async Task<ActionResult<PersonaDto>> GetById(int cc)
        {
            var persona = await _personas.GetByIdAsync(cc);
            if (persona == null) return NotFound();
            return Ok(PersonaDto.FromEntity(persona));
        }

        [HttpPost]
        [ProducesResponseType(typeof(PersonaDto), StatusCodes.Status201Created)]
        [ProducesResponseType(StatusCodes.Status400BadRequest)]
        [ProducesResponseType(StatusCodes.Status409Conflict)]
        public async Task<ActionResult<PersonaDto>> Create(PersonaDto dto)
        {
            if (await _personas.ExistsAsync(dto.Cc))
                return Conflict(new ProblemDetails { Title = $"Ya existe una persona con cc {dto.Cc}." });

            await _personas.AddAsync(dto.ToEntity());
            return CreatedAtAction(nameof(GetById), new { cc = dto.Cc }, dto);
        }

        [HttpPut("{cc:int}")]
        [ProducesResponseType(StatusCodes.Status204NoContent)]
        [ProducesResponseType(StatusCodes.Status400BadRequest)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        public async Task<IActionResult> Update(int cc, PersonaDto dto)
        {
            if (cc != dto.Cc)
                return BadRequest(new ProblemDetails { Title = "La cc de la ruta no coincide con la del cuerpo." });
            if (!await _personas.ExistsAsync(cc)) return NotFound();

            await _personas.UpdateAsync(dto.ToEntity());
            return NoContent();
        }

        [HttpDelete("{cc:int}")]
        [ProducesResponseType(StatusCodes.Status204NoContent)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        [ProducesResponseType(StatusCodes.Status409Conflict)]
        public async Task<IActionResult> Delete(int cc)
        {
            if (!await _personas.ExistsAsync(cc)) return NotFound();

            try
            {
                await _personas.DeleteAsync(cc);
            }
            catch (DbUpdateException)
            {
                return Conflict(new ProblemDetails
                {
                    Title = "No se puede eliminar la persona porque tiene telefonos o estudios asociados."
                });
            }
            return NoContent();
        }
    }
}
