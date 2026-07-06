---
event: 8.8 Gobierno
type: cfp-abstract
language: es
word_limit: 500
created: 2026-04-18
status: draft
data_snapshot: "2026-04-19 — scrape completo: 554 sitios procesados, 478 alcanzados con éxito (status=ok)."
---

# Estado del Consentimiento Web en Chile 2026

**Expositor(es):** {NOMBRE_EXPOSITOR} ({AFILIACION})

**Repositorio:** https://github.com/Privaicl/chile-state-of-web-consent
**Investigación estudiantil:** {SI_O_NO}

---
Área: Estudios de campo de tecnología de seguridad o privacidad
¿Tiene el ciudadano chileno conciencia de la información que es transferida a terceros mediante las cookies que se instalan en su navegador cuando accede a ClaveÚnica — la credencial digital operada bajo el Servicio de Registro Civil e Identificación — para realizar trámites con el Estado? Más generalmente, ¿qué fracción del ecosistema web chileno solicita consentimiento informado antes de depositar mecanismos de seguimiento en quienes lo visitan, y cuántos sitios respetan efectivamente la decisión del usuario que opta por rechazarlos? Estas preguntas, hasta ahora sin respuesta sistemática en la literatura local, motivan el presente estudio empírico, cuya pertinencia se vuelve apremiante en el contexto de la entrada en vigor, en diciembre de 2026, de la Ley 21.719 sobre protección de datos personales.

Para responder estas preguntas se desarrolló un instrumento open-source basado en Patchright (Chromium con stealth) que visita una muestra de 100 sitios curados y 454 sitios del ranking de tráfico chileno, deduplicados por dominio registrable, bajo tres escenarios por sitio: `baseline`, `aceptar` y `rechazar`. En cada escenario se capturan las cookies depositadas y los dominios de terceros contactados. La detección y clasificación de banners, botones y cookies de cola larga se delega a cinco agentes Gemini Flash, que operan únicamente durante la captura con caché versionada por prompt. Cada clasificación queda respaldada por capturas de pantalla del banner y los botones, y por un mecanismo de etiquetado humano para validación independiente. La metodología porta sin modificaciones la regla de cumplimiento mínimo de Nouwens et al. (CHI '25), lo que permite comparar la cifra chilena con la cifra europea de referencia (15%).

Sobre los 478 sitios alcanzados con éxito, los resultados muestran que apenas el 12.6% presenta banner de consentimiento; de éstos, sólo el 33.3% ofrece un botón de rechazo, y se identificaron 21 sitios que continúan depositando cookies de analítica o publicidad tras un rechazo explícito. La cifra chilena de cumplimiento mínimo se ubica en 21.9%, superior al promedio europeo, lo cual matiza la lectura inicial: el problema no es la *ausencia* generalizada de banners conformes, sino su *escasez*, agravada por una práctica masiva de seguimiento sin consulta — 416 de 478 sitios (87%) depositan cookies de tracking antes de cualquier interacción del usuario. El sector gobierno presenta el patrón más severo y uniforme: los 30 dominios `.gob.cl` alcanzados no muestran banner alguno, y 25 de ellos depositan cookies de Google Analytics u otros trackers en la primera carga. Entre los servicios afectados se encuentran ministerios, superintendencias y la propia ClaveÚnica.

Las observaciones tipifican conductas directamente exigibles bajo la Ley 21.719, alineándose con antecedentes regulatorios europeos (CNIL Francia, Garante Italiano y Austrian DPA, 2022) sobre la transferencia de datos personales a proveedores publicitarios extraterritoriales. La charla incluye una demostración en vivo del instrumento y la regeneración determinística del informe — sin invocaciones adicionales a modelos de lenguaje — desde una base de datos versionada, todo disponible públicamente en https://github.com/Privaicl/chile-state-of-web-consent para verificación independiente y extensión.
