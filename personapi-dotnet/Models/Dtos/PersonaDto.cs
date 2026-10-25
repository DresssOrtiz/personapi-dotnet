using System.ComponentModel.DataAnnotations;
using personapi_dotnet.Models.Entities;

namespace personapi_dotnet.Models.Dtos
{
    public class PersonaDto
    {
        [Range(1, int.MaxValue)]
        public int Cc { get; set; }

        [Required, StringLength(45)]
        public string Nombre { get; set; } = null!;

        [Required, StringLength(45)]
        public string Apellido { get; set; } = null!;

        /// <summary>M (masculino) o F (femenino).</summary>
        [Required, RegularExpression("^[MF]$", ErrorMessage = "El genero debe ser 'M' o 'F'.")]
        public string Genero { get; set; } = null!;

        [Range(0, 150)]
        public int? Edad { get; set; }

        public static PersonaDto FromEntity(Persona p) => new()
        {
            Cc = p.Cc,
            Nombre = p.Nombre,
            Apellido = p.Apellido,
            Genero = p.Genero,
            Edad = p.Edad
        };

        public Persona ToEntity() => new()
        {
            Cc = Cc,
            Nombre = Nombre,
            Apellido = Apellido,
            Genero = Genero,
            Edad = Edad
        };
    }
}
