# Estado del Consentimiento Web en Chile — Reporte agregado

*Generado:* `2026-04-18T22:02:42+00:00`
*DB:* `results/study.db`  *git:* `e1552f07b29fef92607e9acb01cea06b5c2811ef`

> Salida puramente determinística sobre `study.db`. Sin invocaciones a modelos de lenguaje en la fase de reporte.

## 1. Cobertura del estudio

Total de sitios en la base: **328**.

| status | count |
|---|---|
| blocked | 30 |
| ok | 275 |
| timeout | 7 |
| unreachable | 16 |

Por segmento:
| status | gov | other |
|---|---|---|
| blocked | 0 | 30 |
| ok | 16 | 259 |
| timeout | 0 | 7 |
| unreachable | 0 | 16 |

## 2. Detección de banner

| segmento | con banner | cargas ok | % |
|---|---|---|---|
| all | 43 | 275 | 15.6% |
| gov | 0 | 16 | 0.0% |
| other | 43 | 259 | 16.6% |

## 3. CMPs identificados

Sitios con banner: **43**.

| CMP | count |
|---|---|
| <sin CMP reconocida> | 24 |
| OneTrust | 9 |
| Cookie Consent (generic) | 3 |
| HubSpot Cookie | 2 |
| HubSpot Cookie Banner | 2 |
| CookieYes | 1 |
| Moove GDPR (WP plugin) | 1 |
| TrustArc | 1 |

Fuente de identificación (`cmp_source`):
| fuente | count |
|---|---|
| <none> | 24 |
| fingerprint | 15 |
| network | 4 |

## 4. Botones presentes en banners

Base: **43** sitios con banner.

| botón | n | % de banners |
|---|---|---|
| accept | 37 | 86.0% |
| reject | 13 | 30.2% |
| settings | 19 | 44.2% |
| save | 1 | 2.3% |
| pay | 0 | 0.0% |

## 5. UX del botón de rechazo

Sitios con `has_reject=1`: **17**.

Capa donde aparece el rechazo:
| reject_layer | count |
|---|---|
| layer 1 | 16 |
| layer 2 | 0 |
| NULL / desconocido | 1 |

`visual_equal` (botones aceptar/rechazar con prominencia visual similar):
| visual_equal | count |
|---|---|
| sí | 9 |
| no | 8 |
| NULL / desconocido | 0 |

## 6. Cumplimiento determinístico (regla Nouwens)

Banners observados (incluyendo los que un re-scrape posterior pudo no haber detectado): **47**. Cumplen la regla mínima: **9** (19.1% del total observado).

Top fallas (entre banners actualmente detectados):
| regla incumplida | count |
|---|---|
| no_reject_button | 30 |
| accept_more_prominent_than_reject | 8 |
| no_accept_button | 6 |

Sitios mínimamente conformes:
| rank | sitio | CMP | aceptar | rechazar | banner ahora |
|---|---|---|---|---|---|
| 8 | Coca-Cola Chile | OneTrust | Permitirlas todas | Rechazarlas todas | ✓ |
| 30 | NotCo |  | Acepto el uso de cookies | No acepto el uso de cookies | ✗ (perdido en re-scrape) |
| 39 | Masisa | HubSpot Cookie Banner | Aceptar | Rechazar | ✓ |
| 63 | KDM |  | Aceptar todo | Continuar sin consentimiento | ✗ (perdido en re-scrape) |
| 76 | MasterCard Chile | OneTrust | Aceptar cookies | Rechazar todas | ✗ (perdido en re-scrape) |
| 95 | DHL Chile | OneTrust | Aceptar todas las cookies | Sólo lo estrictamente necesario | ✗ (perdido en re-scrape) |
| 105 | HostGator Chile | OneTrust | Aceptar todas las cookies | Rechazarlas todas | ✓ |
| 143 | Sovos | OneTrust | Aceptar todas las cookies | Rechazarlas todas | ✓ |
| 278 | Clinicasesteticas.cl |  | Aceptar | Rechazar | ✓ |

## 7. Cookies de tracking depositadas sin consentimiento (escenario baseline)

**243** sitios depositan cookies de tracking (categorías: advertising, analytics, marketing, social) en la primera carga.

| rank | sitio | segmento | n cookies | n clasificadas LLM |
|---|---|---|---|---|
| 294 | La Hora | other | 321 | 204 |
| 210 | TVN | other | 308 | 195 |
| 215 | Radio Carolina | other | 251 | 135 |
| 328 | Radio Futuro | other | 150 | 62 |
| 296 | Rock&Pop | other | 134 | 49 |
| 124 | Cooperativa.cl | other | 129 | 63 |
| 138 | Publimetro Chile | other | 84 | 21 |
| 145 | RedGol | other | 78 | 24 |
| 14 | Sodimac | other | 66 | 30 |
| 313 | LOS40 Chile | other | 53 | 18 |
| 286 | The Clinic | other | 50 | 15 |
| 235 | Farmex | other | 46 | 25 |
| 12 | Falabella | other | 43 | 21 |
| 35 | AFP Provida | other | 43 | 10 |
| 43 | Tricot | other | 43 | 17 |
| 46 | WOM | other | 39 | 16 |
| 72 | Sky Airline | other | 38 | 11 |
| 132 | ADN Radio Chile | other | 38 | 11 |
| 269 | AIEP | other | 38 | 12 |
| 34 | AFP Cuprum | other | 37 | 9 |
| 47 | Claro Chile | other | 36 | 13 |
| 275 | Seguros SURA Chile | other | 36 | 20 |
| 280 | Yapo.cl | other | 36 | 9 |
| 289 | Sparta Chile | other | 36 | 15 |
| 45 | Movistar Chile | other | 35 | 15 |
| 170 | Meganoticias | other | 35 | 15 |
| 122 | Universidad del Desarrollo | other | 34 | 8 |
| 163 | 24 Horas | other | 32 | 15 |
| 221 | Chilevisión | other | 32 | 8 |
| 50 | Betterfly | other | 31 | 10 |
| 148 | Buk | other | 30 | 14 |
| 68 | La Polar | other | 29 | 12 |
| 143 | Sovos | other | 29 | 15 |
| 156 | INACAP | other | 29 | 8 |
| 244 | El Dínamo | other | 29 | 10 |
| 311 | Agilice | other | 29 | 11 |
| 322 | Universidad Adolfo Ibáñez | other | 29 | 8 |
| 126 | BioBioChile | other | 28 | 10 |
| 147 | ArchDaily en Español | other | 28 | 13 |
| 22 | Colbún | other | 27 | 8 |
| 29 | Gasco | other | 27 | 7 |
| 60 | Salcobrand | other | 27 | 10 |
| 109 | DonWeb | other | 27 | 9 |
| 290 | IACC | other | 27 | 12 |
| 190 | Canal 13 | other | 26 | 3 |
| 300 | AFP Habitat | other | 26 | 5 |
| 233 | ABC (ex-ABCDin) | other | 25 | 8 |
| 326 | Cannon Home | other | 25 | 11 |
| 157 | Transbank | other | 24 | 11 |
| 241 | Chileautos | other | 24 | 7 |

*(Mostrando los primeros 50 de 243; ver `findings.json` para el listado completo.)*

## 8. Efectividad del rechazo

**13** sitios donde el clic 'rechazar' tuvo éxito (`reject_layer NOT NULL`) y aún así se setearon cookies de tracking en el escenario `reject`.

| rank | sitio | segmento | layer | n tracking post-rechazo |
|---|---|---|---|---|
| 156 | INACAP | other | 1 | 29 |
| 143 | Sovos | other | 1 | 28 |
| 141 | Mundo / TuMundo | other | 1 | 14 |
| 240 | Mundo / TuMundo | other | 1 | 14 |
| 252 | Mundo / TuMundo | other | 1 | 14 |
| 49 | Cornershop | other | 1 | 12 |
| 48 | Uber Chile | other | 1 | 5 |
| 278 | Clinicasesteticas.cl | other | 1 | 4 |
| 39 | Masisa | other | 1 | 3 |
| 242 | Recetas Nestlé Chile | other | 1 | 3 |
| 105 | HostGator Chile | other | 1 | 2 |
| 8 | Coca-Cola Chile | other | 1 | 1 |
| 61 | Ripley Corp | other | 1 | 1 |

## 9. Sector gobierno (`*.gob.cl`)

**16** dominios gubernamentales con `status='ok'`.

Resumen por sitio:
| rank | sitio | has_banner | cookies baseline | tracking baseline | CMP |
|---|---|---|---|---|---|
| 102 | Gobierno de Chile | 0 | 8 | 5 |  |
| 103 | Ministerio de Desarrollo Social y Familia | 0 | 6 | 4 |  |
| 135 | Dirección del Trabajo | 0 | 2 | 2 |  |
| 178 | BIPS - Ministerio de Desarrollo Social | 0 | 6 | 2 |  |
| 180 | ClaveÚnica | 0 | 5 | 3 |  |
| 188 | Superintendencia de Salud | 0 | 6 | 5 |  |
| 194 | DGAC | 0 | 4 | 4 |  |
| 196 | SAG | 0 | 5 | 5 |  |
| 202 | Ministerio de Desarrollo Social y Familia | 0 | 6 | 4 |  |
| 216 | RNPI Superintendencia de Salud | 0 | 2 | 0 |  |
| 220 | Ministerio del Medio Ambiente | 0 | 4 | 4 |  |
| 223 | Ministerio de Transportes y Telecomunicaciones | 0 | 0 | 0 |  |
| 254 | Memoria Chilena | 0 | 7 | 7 |  |
| 259 | SAG Plaguicidas | 0 | 1 | 0 |  |
| 267 | ChileAtiende | 0 | 7 | 3 |  |
| 276 | RSH Municipal | 0 | 4 | 0 |  |

## 10. Comparación entre segmentos

| segmento | total | ok | con banner | % con banner |
|---|---|---|---|---|
| gov | 16 | 16 | 0 | 0.0% |
| other | 312 | 259 | 43 | 16.6% |

## 11. Plantillas de banner compartidas (clusters)

Clusters de sitios con prefijo idéntico de `banner_text_snippet` (primeros 100 caracteres normalizados):


### Cluster `89c09967bb0f` — 3 sitios (accept=3, reject=3)
> *Snippet:* `
	
		
		CONDICIONES GENERALES DE USO DEL SITIO WEB
		
			
		
	

	
	
		Este Sitio utiliza cookies para mejorar la experie…`
| rank | sitio | accept | reject | CMP |
|---|---|---|---|---|
| 141 | Mundo / TuMundo | 1 | 1 |  |
| 240 | Mundo / TuMundo | 1 | 1 |  |
| 252 | Mundo / TuMundo | 1 | 1 |  |

### Cluster `1981a8ae8f33` — 2 sitios (accept=2, reject=0)
> *Snippet:* `Usamos cookies para mejorar tu experiencia. Consulta más aquí.Entendido…`
| rank | sitio | accept | reject | CMP |
|---|---|---|---|---|
| 44 | CMR Falabella | 1 | 0 | Cookie Consent (generic) |
| 181 | Banco Falabella | 1 | 0 | Cookie Consent (generic) |

### Cluster `3980a9610309` — 2 sitios (accept=2, reject=0)
> *Snippet:* `Usamos cookies para mejorar tu experiencia. Revisa nuestras política de privacidad y de cookies.Aceptar…`
| rank | sitio | accept | reject | CMP |
|---|---|---|---|---|
| 12 | Falabella | 1 | 0 |  |
| 14 | Sodimac | 1 | 0 |  |

### Cluster `4f3cfd21652d` — 2 sitios (accept=2, reject=2)
> *Snippet:* `Usamos cookiesSelecciona Aceptar para permitir que Uber use cookies y personalice este sitio. Usamos cookies para record…`
| rank | sitio | accept | reject | CMP |
|---|---|---|---|---|
| 48 | Uber Chile | 1 | 1 |  |
| 49 | Cornershop | 1 | 1 |  |

### Cluster `5b17aecddc97` — 2 sitios (accept=0, reject=0)
> *Snippet:* `EntiendoEste sitio utiliza cookies parea mejorar la experiencia y proporcionar funcionalidades adicionales. Para más inf…`
| rank | sitio | accept | reject | CMP |
|---|---|---|---|---|
| 185 | Consorcio | 0 | 0 |  |
| 245 | Banco Consorcio | 0 | 0 |  |

### Cluster `817b0487d9d3` — 2 sitios (accept=2, reject=1)
> *Snippet:* `Al hacer clic en “Aceptar todas las cookies”, usted acepta que las cookies se guarden en su dispositivo para mejorar la …`
| rank | sitio | accept | reject | CMP |
|---|---|---|---|---|
| 24 | AES Andes | 1 | 0 | OneTrust |
| 143 | Sovos | 1 | 1 | OneTrust |

### Cluster `e78ff3697e6b` — 2 sitios (accept=0, reject=0)
> *Snippet:* `
    
        
            Utilizamos cookies
            Usamos cookies para mejorar tu experiencia en el portal. Estas…`
| rank | sitio | accept | reject | CMP |
|---|---|---|---|---|
| 209 | CruzBlanca Isapre | 0 | 0 | HubSpot Cookie |
| 264 | Bupa Chile | 0 | 0 |  |

### Cluster `e96089b92d4c` — 2 sitios (accept=2, reject=0)
> *Snippet:* `¡Usamos cookies para que tu experiencia de navegación sea más segura y personalizada!Descubre más sobre nuestra Política…`
| rank | sitio | accept | reject | CMP |
|---|---|---|---|---|
| 7 | Entel | 1 | 0 | OneTrust |
| 93 | Entel Tower | 1 | 0 | OneTrust |

## 12. Validación de los agentes (F1 contra etiquetas humanas)

*Sin labels humanos en `results/validations/labels.json`. Para activar esta sección: ejecutar `python scripts/label_server.py`, etiquetar desde `results/audit_report.html`, y regenerar el reporte.*
