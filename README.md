# Estado del Consentimiento Web en Chile 2026

Datos, scripts de análisis y reporte derivados de un estudio empírico de las
prácticas de consentimiento de cookies en sitios web chilenos. El estudio se
realizó en abril de 2026 sobre una muestra combinada de 100 sitios de un
listado curado y 454 sitios provenientes de un ranking de tráfico nacional,
deduplicados por dominio registrable.

La metodología porta sin modificaciones la regla de cumplimiento mínimo
propuesta por Nouwens et al. (CHI '25), lo que permite comparar la cifra
chilena con la cifra europea de referencia. Las extensiones respecto al
trabajo original se documentan en el reporte.

> **Alcance del repositorio.** Este repositorio publica los **datos** del
> experimento, los **scripts de análisis** y el **reporte generado** a partir
> de esos datos. La implementación del scraper que produjo `study.db` se
> mantiene fuera del alcance público de este repositorio.

---

## Estructura

```
.
├── companies.json                       # Listado baseline curado (100 sitios)
├── data/
│   ├── companies_traffic.json           # Ranking de tráfico (492 sitios)
│   ├── companies_traffic_new.json       # Tráfico tras dedup contra baseline
│   └── known_cookies.csv                # Open Cookie Database (clasificación tier-1)
├── results/
│   ├── study.db                         # Base SQLite con todos los resultados experimentales
│   └── study_report/                    # Reporte agregado (regenerable)
│       ├── INDEX.md
│       ├── summary.md                   # Hallazgos agregados (todas las tablas)
│       ├── findings.json                # Datos crudos en formato maquinable
│       ├── segments/{gov,other}.md
│       └── per_site/<rank>.md           # Fichas individuales selectivas
├── scripts/
│   ├── dedup_traffic.py                 # Dedup baseline ∪ traffic por dominio registrable
│   ├── study_report.py                  # Generador del reporte (sin LLM)
│   ├── build_audit_report.py            # Genera audit_report.html para validación humana
│   ├── compute_agent_f1.py              # Precision/recall/F1 de los agentes contra labels
│   └── label_server.py                  # Servidor HTTP local para etiquetado manual
└── (raíz: LICENSE, CITATION.cff, pyproject.toml, README.md)
```

---

## Cómo regenerar el reporte

El reporte es **puramente determinístico**: no realiza ninguna invocación a
modelos de lenguaje. Todas las clasificaciones LLM ya están persistidas en
`results/study.db` (con caché versionada por prompt), y se consumen tal como
están.

```bash
# Instalación mínima
python -m venv .venv && source .venv/bin/activate
pip install tldextract

# Regenerar el reporte
python scripts/study_report.py
# → escribe results/study_report/

# (Opcional) regenerar la deduplicación del listado de tráfico
python scripts/dedup_traffic.py
# → escribe data/companies_traffic_new.json
```

Dos ejecuciones consecutivas sobre el mismo `study.db` producen output
bit-idéntico — así se garantiza la verificabilidad por terceros.

---

## Modelo de amenaza asumido

El análisis de las cookies depositadas asume el modelo estándar para Google
Analytics y proveedores publicitarios extraterritoriales: el identificador
de cliente persistido en `_ga` (más IP, User-Agent y referrer/path) permite
reconstruir, server-side, el patrón de navegación de un usuario individual
a través de las propiedades instrumentadas con `gtag.js` u otros píxeles
análogos.

---

## Licencia

MIT — ver [`LICENSE`](LICENSE).

---

## Cómo citar este proyecto

Si utiliza este dataset, los scripts o el reporte en trabajo derivado
(académico, regulatorio, periodístico u otro), se agradece la siguiente
cita:

**Formato simple (texto):**

> Varas, N., Escobar, E., y Wagemann, K. (2026). *Estado del Consentimiento
> Web en Chile 2026.* Nickel Technologies SpA.
> https://github.com/Privaicl/chile-state-of-web-consent

**BibTeX:**

```bibtex
@misc{varas2026chile_consent,
  author       = {Varas, Nicolás and Escobar, Edison and Wagemann, Kelly},
  title        = {Estado del Consentimiento Web en Chile 2026},
  year         = {2026},
  publisher    = {Nickel Technologies SpA},
  howpublished = {\url{https://github.com/Privaicl/chile-state-of-web-consent}},
}
```

Una versión maquinable de los metadatos de cita está disponible en
[`CITATION.cff`](CITATION.cff), lo que activa el botón *"Cite this
repository"* en la interfaz de GitHub.
