-- Laboratorio 1 - personapi-dotnet
-- DDL para SQL Server (adaptado del modelo MySQL del laboratorio)
-- Ejecutar conectado a la instancia (base master).

IF DB_ID(N'persona_db') IS NULL
    CREATE DATABASE persona_db;
GO

USE persona_db;
GO

-- La propiedad de la base de datos pertenece al usuario sa
ALTER AUTHORIZATION ON DATABASE::persona_db TO sa;
GO

IF OBJECT_ID(N'dbo.estudios', N'U') IS NOT NULL DROP TABLE dbo.estudios;
IF OBJECT_ID(N'dbo.telefono',  N'U') IS NOT NULL DROP TABLE dbo.telefono;
IF OBJECT_ID(N'dbo.profesion', N'U') IS NOT NULL DROP TABLE dbo.profesion;
IF OBJECT_ID(N'dbo.persona',   N'U') IS NOT NULL DROP TABLE dbo.persona;
GO

CREATE TABLE dbo.persona (
    cc       INT           NOT NULL,
    nombre   VARCHAR(45)   NOT NULL,
    apellido VARCHAR(45)   NOT NULL,
    genero   CHAR(1)       NOT NULL,
    edad     INT           NULL,
    CONSTRAINT PK_persona PRIMARY KEY (cc),
    CONSTRAINT CK_persona_genero CHECK (genero IN ('M', 'F')),
    CONSTRAINT CK_persona_edad CHECK (edad IS NULL OR edad >= 0)
);
GO

CREATE TABLE dbo.profesion (
    id  INT           NOT NULL,
    nom VARCHAR(90)   NOT NULL,
    des VARCHAR(MAX)  NULL,
    CONSTRAINT PK_profesion PRIMARY KEY (id)
);
GO

CREATE TABLE dbo.telefono (
    num    VARCHAR(15) NOT NULL,
    oper   VARCHAR(45) NOT NULL,
    duenio INT         NOT NULL,
    CONSTRAINT PK_telefono PRIMARY KEY (num),
    CONSTRAINT FK_telefono_persona FOREIGN KEY (duenio) REFERENCES dbo.persona (cc)
);
GO

CREATE INDEX IX_telefono_duenio ON dbo.telefono (duenio);
GO

CREATE TABLE dbo.estudios (
    id_prof INT         NOT NULL,
    cc_per  INT         NOT NULL,
    fecha   DATE        NULL,
    univer  VARCHAR(50) NULL,
    CONSTRAINT PK_estudios PRIMARY KEY (id_prof, cc_per),
    CONSTRAINT FK_estudios_profesion FOREIGN KEY (id_prof) REFERENCES dbo.profesion (id),
    CONSTRAINT FK_estudios_persona   FOREIGN KEY (cc_per)  REFERENCES dbo.persona (cc)
);
GO

CREATE INDEX IX_estudios_cc_per ON dbo.estudios (cc_per);
GO
