import json,os,sys
from playwright.sync_api import sync_playwright
BASE="http://127.0.0.1:5000"; EJ=sys.argv[1]; OUT=sys.argv[2]
res={}
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(accept_downloads=True,viewport={"width":1400,"height":1000}); pg=ctx.new_page()
    pg.goto(BASE+"/admin/ingreso"); pg.fill("[name=usuario]","investigadora"); pg.fill("[name=contrasena]","clave-segura-1"); pg.click("text=Ingresar")
    for n in (1,2):
        pg.goto(BASE+"/admin/reportes")
        pg.select_option("[name=id_equipo]",index=n-1 if pg.locator("[name=id_equipo] option").first.get_attribute("value") else n)
        pg.fill("[name=periodo_inicio]","2026-03-01"); pg.fill("[name=periodo_fin]","2026-05-15")
        pg.set_input_files("[name=archivo]",f"{EJ}/metricas_demo_equipo_{n}.csv"); pg.click("text=Validar y cargar")
        pg.screenshot(path=OUT+f"/paso_carga_{n}.png")
    pg.goto(BASE+"/admin/emparejamiento"); pg.click("text=Ejecutar emparejamiento")
    pg.goto(BASE+"/admin/analisis"); pg.click("text=Ejecutar análisis")
    pg.goto(BASE+"/admin/dashboard"); pg.screenshot(path=OUT+"/dbg.png",full_page=True); print(pg.url, pg.locator("#avisos").inner_text()[:300]); pg.wait_for_selector("#tabla-correlaciones tbody tr", timeout=15000)
    pg.wait_for_timeout(1500)
    filas=pg.locator("#tabla-correlaciones tbody tr")
    total=filas.count(); sig=pg.locator("#tabla-correlaciones tbody tr.significativo").count()
    # Verificación cruzada: cada fila resaltada debe tener p<0,05 en la API
    api=pg.evaluate("fetch('/admin/api/dashboard').then(r=>r.json())")
    cor=api["correlaciones"]; sig_api=sum(1 for c in cor if c["p_valor"]<0.05)
    ok_cls=all(('significativo' in (filas.nth(i).get_attribute('class') or ''))==(cor[i]['p_valor']<0.05) for i in range(min(total,len(cor))))
    etq=pg.locator("#tabla-correlaciones .etiqueta.aviso").count()
    pg.screenshot(path=OUT+"/dashboard.png",full_page=True)
    res["CP18"]={"filas":total,"resaltadas":sig,"significativas_api":sig_api,"coincide_fila_a_fila":ok_cls,"etiquetas_significativo":etq}
    # CP-19 exportar PNG
    with pg.expect_download() as d: pg.click("[data-exportar=grafico-correlaciones]")
    dl=d.value; ruta=OUT+"/grafico-correlaciones.png"; dl.save_as(ruta)
    from PIL import Image
    im=Image.open(ruta); im.load()
    res["CP19_png"]={"archivo":dl.suggested_filename,"bytes":os.path.getsize(ruta),"tam":list(im.size)}
    # CP-19 exportar PDF (impresión del dashboard)
    pg.emulate_media(media="print"); pg.pdf(path=OUT+"/dashboard.pdf",format="A4",print_background=True)
    res["CP19_pdf"]={"bytes":os.path.getsize(OUT+"/dashboard.pdf"),"boton_pdf":pg.locator("#boton-pdf").count()}
    b.close()
json.dump(res,open(OUT+"/resultado_navegador.json","w"),indent=1); print(json.dumps(res,indent=1))
