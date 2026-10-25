-- Laboratorio 1 - personapi-dotnet
-- DML: datos de prueba para persona_db

USE persona_db;
GO

INSERT INTO dbo.persona (cc, nombre, apellido, genero, edad) VALUES
    (1001, 'Andres',   'Ortiz',      'M', 21),
    (1002, 'Tomas',    'Ramirez',    'M', 22),
    (1003, 'Santiago', 'Hernandez',  'M', 21),
    (1004, 'Laura',    'Gomez',      'F', 30),
    (1005, 'Camila',   'Torres',     'F', 27);
GO

INSERT INTO dbo.profesion (id, nom, des) VALUES
    (1, 'Ingeniero de Sistemas', 'Diseno, desarrollo y mantenimiento de sistemas de software'),
    (2, 'Administrador de Empresas', 'Gestion y direccion de organizaciones'),
    (3, 'Disenador Grafico', 'Creacion de piezas visuales y comunicacion grafica'),
    (4, 'Medico', 'Prevencion, diagnostico y tratamiento de enfermedades');
GO

INSERT INTO dbo.telefono (num, oper, duenio) VALUES
    ('3001112233', 'Claro',    1001),
    ('3104445566', 'Movistar', 1001),
    ('3207778899', 'Tigo',     1002),
    ('3015550011', 'Claro',    1003),
    ('3126663344', 'WOM',      1004);
GO

INSERT INTO dbo.estudios (id_prof, cc_per, fecha, univer) VALUES
    (1, 1001, '2026-06-15', 'Pontificia Universidad Javeriana'),
    (1, 1002, '2026-06-15', 'Pontificia Universidad Javeriana'),
    (1, 1003, '2026-06-15', 'Pontificia Universidad Javeriana'),
    (2, 1004, '2018-12-10', 'Universidad de los Andes'),
    (3, 1005, '2021-05-20', 'Universidad Nacional de Colombia'),
    (4, 1004, '2023-11-30', 'Universidad del Rosario');
GO
