using System.ComponentModel.DataAnnotations;
using personapi_dotnet.Models.Entities;

namespace personapi_dotnet.Models.Dtos
{
    public class ProfesionDto
    {
        [Range(1, int.MaxValue)]
        public int Id { get; set; }

        [Required, StringLength(90)]
        public string Nom { get; set; } = null!;

        public string? Des { get; set; }

        public static ProfesionDto FromEntity(Profesion p) => new()
        {
            Id = p.Id,
            Nom = p.Nom,
            Des = p.Des
        };

        public Profesion ToEntity() => new()
        {
            Id = Id,
            Nom = Nom,
            Des = Des
        };
    }
}
