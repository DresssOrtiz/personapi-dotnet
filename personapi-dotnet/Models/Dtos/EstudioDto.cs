using System.ComponentModel.DataAnnotations;
using personapi_dotnet.Models.Entities;

namespace personapi_dotnet.Models.Dtos
{
    public class EstudioDto
    {
        /// <summary>Identificador de la profesion.</summary>
        [Range(1, int.MaxValue)]
        public int IdProf { get; set; }

        /// <summary>Cedula de la persona.</summary>
        [Range(1, int.MaxValue)]
        public int CcPer { get; set; }

        public DateTime? Fecha { get; set; }

        [StringLength(50)]
        public string? Univer { get; set; }

        public static EstudioDto FromEntity(Estudio e) => new()
        {
            IdProf = e.IdProf,
            CcPer = e.CcPer,
            Fecha = e.Fecha,
            Univer = e.Univer
        };

        public Estudio ToEntity() => new()
        {
            IdProf = IdProf,
            CcPer = CcPer,
            Fecha = Fecha,
            Univer = Univer
        };
    }
}
