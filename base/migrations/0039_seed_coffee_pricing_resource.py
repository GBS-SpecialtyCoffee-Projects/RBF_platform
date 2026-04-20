from django.db import migrations


SLUG = "fijacion-de-precios-del-cafe"
TITLE = "Fijación de Precios del Café"
SUMMARY = (
    "El precio al que uno vende su café es una decisión estratégica "
    "que determina la viabilidad de la operación cafetera."
)

BODY = """\
<p>El precio al que uno vende su café es una decisión estratégica que determina la viabilidad de la operación cafetera. No hay una sola metodología para encontrar el precio "correcto" o "justo", pero existen varias estrategias comunes que pueden evaluar. Al fin de cuentas, tienen que evaluar cuáles de estos factores necesitan considerar según su situación personal para asegurarse que la caficultura les permite satisfacer sus necesidades, y que hace que la caficultura "valga la pena" para ustedes, además de ser un precio accesible en el mercado.</p>

<h3>Estrategias Internas</h3>
<p>Una opción sencilla y común es el método del coste incrementado, empezando por su costo de producción del café, y agregando el ingreso personal necesario o deseado de los propietarios de la finca. Este método sirve para establecer un precio base, debajo del cual, la caficultura deja de ser viable, y por eso, no deben sobrepasar en la venta.</p>
<pre><code>costo de producción por unidad de café producido = (gasto total de producción de café) / (volumen de café producido)</code></pre>

<h3>Método del Ingreso Necesario</h3>
<p>Para incluir este elemento importante en la estrategia de precios del café, se debe crear un presupuesto (monetario) anual de las personas que dependen de la finca para su sustento. Este número total se puede dividir por la cantidad de café que venden (con cualquier unidad de medida) para saber el margen necesario de subsistencia por unidad de café producido. Este margen de subsistencia se puede agregar al costo de producción del café para calcular su precio mínimo de subsistencia.</p>
<pre><code>Margen de subsistencia = (presupuesto familiar de subsistencia) / (volumen de café producido)</code></pre>
<pre><code>Precio de subsistencia = (costo de producción por unidad) + (margen de subsistencia)</code></pre>

<h3>Tasa de Ganancia</h3>
<p>Menos común para los participantes en el Coffee Circuit (circuito del café) pero un método importante para operaciones netamente capitalistas (invierten capital para generar ganancias) se enfoca en la tasa de ganancia, o tasa interna de rendimiento. Bajo esa lógica, sólo tiene sentido mantener la inversión en la operación cafetera cuando esta genera un mayor rendimiento sobre el capital invertido que las otras posibles inversiones.</p>

<h3>Estrategias Comparativas</h3>
<p>Mientras las estrategias mencionadas arriba se enfocan en proteger la viabilidad de la operación cafetera estableciendo precios mínimos, no tocan la noción de precios justos y no consideran la capacidad del comprador de pagarlos. Una estrategia menos defensiva que considere estos dos aspectos es la participación en la venta final. Si el precio al consumidor es el tamaño de la torta, y tiene mucho que ver con la calidad de café que sale de la finca, ¿qué porcentaje de este merece ganar el productor? No hay una sola respuesta, pero según este estudio de cafés de especialidad, ronda el 16-20%. Hay empresas que usan esto como regla, como Toque Coffee, que asegura que los productores ganan el 20% de su precio de venta. Aunque este método se enfoca en el precio que soporta el mercado de consumo, no ofrece ninguna garantía de que este sea mayor al precio mínimo de subsistencia de la familia productora, así que vale la pena considerar los precios desde diferentes perspectivas.</p>

<h3>Comparación de Precios del Mercado</h3>
<p>Otro método de establecer precios es con base en la comparación, o con base en los precios que los demás están cobrando y que los compradores se han mostrado dispuestos a pagar. ¿Pero cómo se sabe eso? Para responder esta pregunta existe la "Guía de Transacciones de Cafés Especiales", una iniciativa del mismo grupo de académicos-activistas detrás de esta plataforma. Con esta herramienta, pueden saber el rango de precios a los que suelen vender cafés con las mismas características que el suyo, con base en el país de origen, el tamaño del lote, y el rango de puntajes de taza. Este método no indica el precio ni justo ni correcto necesariamente, sino ofrece una reflexión de la disposición del mercado durante la cosecha anterior, y por eso puede representar una comparación interesante para entender qué tan razonable puede sonar su precio a un comprador potencial.</p>

<h3>El Precio del Mercado</h3>
<p>Aunque estas estrategias consideran las necesidades de los productores y la capacidad de los compradores, la noción de un solo "precio del mercado" basado en indicadores mundiales suele dominar la conversación sobre los precios, aunque en varios sentidos está alejado de la realidad tanto de los productores como los consumidores. Cuando se habla del "precio del mercado", eso no quiere decir que es un precio justo, natural, or que emerge según las fuerzas del libre mercado, sino es el precio acordado entre un consenso de actores del mercado y puede no tener nada que ver con la oferta y la demanda del tipo de café que usted vende.</p>
<p>El precio del mercado de Nueva York, por ejemplo, es el precio promedio de transacciones de contratos de futuros de café, los cuales se pueden cambiar por café físico, técnicamente, pero casi nunca sucede. Además, existe evidencia contundente de que ese indicador no responde directamente a los cambios de oferta y demanda del mercado físico, y por eso no promueve el equilibrio del mercado, y entonces, desviarse del precio de ese instrumento no conlleva el riesgo de "dañar el mercado" o crear sobreoferta invendible. Los indicadores de precios de la Organización Internacional del Café (OIC) son las referencias más comunes en la industria del café y las transacciones tienden a reflejarse fielmente. Sin embargo, aunque estos números difieren levemente del precio Nueva York, siguen altamente correlacionados con éste y entre sí, y según nuestro análisis, no compensan las diferencias del mercado físico, y por eso no deben considerarse precios justos o de equilibrio. Aparte de eso, estas referencias especifican una calidad nacional o regional promedio, sin considerar las potenciales características sensoriales diferenciadas del café que usted produce.</p>

<h3>Metodologías y Términos de Precios</h3>
<p>Además del nivel de precio negociado, es necesario establecer la metodología de fijación y la moneda. Lo más sencillo y común en el caso de café de especialidad es el precio fijo que se establece al momento de hacer un acuerdo y se paga a pesar de los indicadores. Suena seguro, pero igualmente puede implicar riesgos. Por un lado, el vendedor asume riesgo cuando los costos fluctúan, por ejemplo una exportadora o cooperativa que les paga a los productores según un precio mínimo de referencia que podría subir. Para cambiar la estructura y la distribución del riesgo, también se puede acordar el precio "por diferencial" o acordando un monto relativo a (más o menos de) un indicador, que en el café arábigo suele ser el "precio Nueva York" o la cotización del contrato de futuro "KC" de la bolsa ICE. En ese caso, hay un precio base que fluctúa y un diferencial acordado. El momento clave es la fijación de la base que puede ser elegida por el vendedor ("seller's call") o asociado con un hito del proceso logístico, por ejemplo el zarpe del buque que transporta el café o la emisión de la carta de porte.</p>
<p>Por otro lado, cuando se establece el precio en una moneda extranjera, el monto que el vendedor recibe y el monto que el comprador paga puede variar según la tasa de cambio. En el café, es común cotizar precios en dólares estadounidenses aunque la mayoría de los productores no reciben esa moneda y la mayoría de los compradores no la pagan. Cuando se fija el precio en la moneda del vendedor, es el comprador quien asume el riesgo de la tasa de cambio, y viceversa.</p>
"""


def seed_resource(apps, schema_editor):
    Resource = apps.get_model("base", "Resource")
    Resource.objects.update_or_create(
        slug=SLUG,
        defaults={
            "title": TITLE,
            "summary": SUMMARY,
            "body": BODY,
            "is_published": True,
        },
    )


def unseed_resource(apps, schema_editor):
    Resource = apps.get_model("base", "Resource")
    Resource.objects.filter(slug=SLUG).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("base", "0038_roaster_country_code"),
    ]

    operations = [
        migrations.RunPython(seed_resource, unseed_resource),
    ]
