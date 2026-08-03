# ADR-001 — DOBO CAD Kernel Philosophy

**Status:** Accepted

**Date:** 2026-08-03

**Version:** 2.0

---

# 1. Context

DOBO nació como un generador paramétrico de macetas utilizando CadQuery.

Durante su evolución fueron apareciendo nuevos módulos especializados para resolver problemas concretos:

- generación del cuerpo
- drenaje
- texto
- patrones
- geometría
- superficies
- registros de plugins

Con el tiempo quedó claro que estos componentes no dependían exclusivamente de una maceta, sino que podían reutilizarse para generar cualquier tipo de geometría paramétrica.

Esta evolución cambió la naturaleza del proyecto.

DOBO dejó de ser únicamente un generador de objetos y comenzó a convertirse en un núcleo geométrico reutilizable.

---

# 2. Problema

A medida que el proyecto crece aparecen nuevos desafíos:

- duplicación de lógica
- módulos con múltiples responsabilidades
- dependencias innecesarias
- dificultad para incorporar nuevas capacidades
- crecimiento del código sin una arquitectura común

Sin una filosofía clara el motor terminaría convirtiéndose en una colección de funcionalidades independientes.

---

# 3. Decisión

El proyecto adopta una arquitectura basada en motores independientes con responsabilidades únicas.

DOBO pasa a definirse como un **Kernel CAD Paramétrico** compuesto por componentes desacoplados que colaboran mediante interfaces bien definidas.

Cada nuevo módulo deberá integrarse en esta arquitectura sin romper los principios establecidos en este documento.

---

# 4. Principios

## 4.1 Una responsabilidad por componente

Cada motor debe resolver un único problema.

No debe asumir responsabilidades adicionales.

---

## 4.2 Toda geometría comienza en dos dimensiones

Los proveedores generan únicamente geometría 2D.

La creación de sólidos pertenece a una etapa posterior del pipeline.

---

## 4.3 Los componentes deben ser reutilizables

Un componente no debe conocer el producto final.

Debe poder reutilizarse en cualquier contexto.

---

## 4.4 La arquitectura tiene prioridad sobre la implementación

Antes de escribir código debe existir una decisión de arquitectura.

Las implementaciones pueden cambiar.

La arquitectura debe permanecer estable.

---

## 4.5 Los motores colaboran mediante interfaces

Los motores nunca deben depender de implementaciones concretas.

Toda comunicación se realiza mediante interfaces claramente definidas.

---

## 4.6 La extensibilidad es un objetivo del diseño

Agregar nuevas capacidades debe requerir crear nuevos componentes, no modificar los existentes.

El sistema debe crecer mediante extensión y no mediante modificación continua.

---

# 5. Objetivos

DOBO busca convertirse en un kernel geométrico capaz de soportar:

- diseño paramétrico
- fabricación digital
- impresión 3D
- generación procedural
- reutilización de componentes
- automatización mediante IA

La generación de macetas representa únicamente una de las aplicaciones posibles del motor.

---

# 6. No Objetivos

DOBO no pretende reemplazar sistemas CAD completos.

No pretende competir con motores de modelado de propósito general.

Su objetivo es proporcionar un núcleo especializado para la generación paramétrica de geometría.

---

# 7. Consecuencias

A partir de esta decisión:

- toda nueva funcionalidad deberá respetar la arquitectura del Kernel;
- las decisiones importantes se documentarán mediante ADR;
- la arquitectura tendrá prioridad sobre la implementación concreta;
- el crecimiento del proyecto estará guiado por principios y no únicamente por necesidades inmediatas.

---

# 8. Visión

DOBO evoluciona desde un generador de objetos hacia una plataforma geométrica modular.

El objetivo es construir un núcleo estable, extensible y reutilizable capaz de servir como base para futuras herramientas de diseño paramétrico y fabricación digital.