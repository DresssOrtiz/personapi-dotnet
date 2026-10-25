using Microsoft.AspNetCore.Mvc;
using personapi_dotnet.Interfaces;
using personapi_dotnet.Models.Dtos;

namespace personapi_dotnet.Controllers.Api
{
    [ApiController]
    [Route("api/telefonos")]
    [Produces("application/json")]
    public class TelefonosController : ControllerBase
    {
        private readonly ITelefonoRepository _telefonos;
        private readonly IPersonaRepository _personas;

        public TelefonosController(ITelefonoRepository telefonos, IPersonaRepository personas)
        {
            _telefonos = telefonos;
            _personas = personas;
        }

        [HttpGet]
        [ProducesResponseType(typeof(IEnumerable<TelefonoDto>), StatusCodes.Status200OK)]
        public async Task<ActionResult<IEnumerable<TelefonoDto>>> GetAll()
        {
            var telefonos = await _telefonos.GetAllAsync();
            return Ok(telefonos.Select(TelefonoDto.FromEntity));
        }

        [HttpGet("{num}")]
        [ProducesResponseType(typeof(TelefonoDto), StatusCodes.Status200OK)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        public async Task<ActionResult<TelefonoDto>> GetById(string num)
        {
            var telefono = await _telefonos.GetByIdAsync(num);
            if (telefono == null) return NotFound();
            return Ok(TelefonoDto.FromEntity(telefono));
        }

        [HttpPost]
        [ProducesResponseType(typeof(TelefonoDto), StatusCodes.Status201Created)]
        [ProducesResponseType(StatusCodes.Status400BadRequest)]
        [ProducesResponseType(StatusCodes.Status409Conflict)]
        public async Task<ActionResult<TelefonoDto>> Create(TelefonoDto dto)
        {
            if (!await _personas.ExistsAsync(dto.Duenio))
                return BadRequest(new ProblemDetails { Title = $"No existe una persona con cc {dto.Duenio}." });
            if (await _telefonos.ExistsAsync(dto.Num))
                return Conflict(new ProblemDetails { Title = $"Ya existe el telefono {dto.Num}." });

            await _telefonos.AddAsync(dto.ToEntity());
            return CreatedAtAction(nameof(GetById), new { num = dto.Num }, dto);
        }

        [HttpPut("{num}")]
        [ProducesResponseType(StatusCodes.Status204NoContent)]
        [ProducesResponseType(StatusCodes.Status400BadRequest)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        public async Task<IActionResult> Update(string num, TelefonoDto dto)
        {
            if (num != dto.Num)
                return BadRequest(new ProblemDetails { Title = "El numero de la ruta no coincide con el del cuerpo." });
            if (!await _telefonos.ExistsAsync(num)) return NotFound();
            if (!await _personas.ExistsAsync(dto.Duenio))
                return BadRequest(new ProblemDetails { Title = $"No existe una persona con cc {dto.Duenio}." });

            await _telefonos.UpdateAsync(dto.ToEntity());
            return NoContent();
        }

        [HttpDelete("{num}")]
        [ProducesResponseType(StatusCodes.Status204NoContent)]
        [ProducesResponseType(StatusCodes.Status404NotFound)]
        public async Task<IActionResult> Delete(string num)
        {
            if (!await _telefonos.ExistsAsync(num)) return NotFound();

            await _telefonos.DeleteAsync(num);
            return NoContent();
        }
    }
}
