using System.ComponentModel.DataAnnotations;
using personapi_dotnet.Models.Entities;

namespace personapi_dotnet.Models.Dtos
{
    public class TelefonoDto
    {
        [Required, StringLength(15)]
        public string Num { get; set; } = null!;

        [Required, StringLength(45)]
        public string Oper { get; set; } = null!;

        /// <summary>Cedula de la persona propietaria.</summary>
        [Range(1, int.MaxValue)]
        public int Duenio { get; set; }

        public static TelefonoDto FromEntity(Telefono t) => new()
        {
            Num = t.Num,
            Oper = t.Oper,
            Duenio = t.Duenio
        };

        public Telefono ToEntity() => new()
        {
            Num = Num,
            Oper = Oper,
            Duenio = Duenio
        };
    }
}
