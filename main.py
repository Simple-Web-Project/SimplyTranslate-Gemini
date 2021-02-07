from jetforce import GeminiServer, JetforceApplication, Response, Status
from simplytranslate_engines import (googletranslate, libretranslate)

page_header = """```
   _____            __    ______                  __     __     
  / __(_)_ _  ___  / /_ _/_  __/______ ____  ___ / /__ _/ /____ 
 _\ \/ /  ' \/ _ \/ / // // / / __/ _ `/ _ \(_-</ / _ `/ __/ -_)
/___/_/_/_/_/ .__/_/\_, //_/ /_/  \_,_/_//_/___/_/\_,_/\__/\__/ 
           /_/     /___/                                        
```"""

app = JetforceApplication()


# TODO: find a better name.
def to_lang_code(lang, supported_languages):
    if lang == "Autodetect" or lang == "auto":
        return "auto"

    if lang in supported_languages.keys():
        return supported_languages[lang]
    
    if lang in supported_languages.values():
        return lang

@app.route("")
@app.route("/(?P<engine>google|libre)/(?P<fr>\S+)/(?P<to>\S+)")
@app.route("/(?P<engine>google|libre)/(?P<fr>\S+)/(?P<to>\S+)/(?P<text>\S+)")
@app.route("/(?P<engine>google|libre)/(?P<fr>\S+)/(?P<to>\S+)/(?P<text>.*)")
def index(request, engine="google", fr="auto", to="English", text=""):


    #TODO: use some better function for this
    escaped_text = text.replace(" ", "%20")
    
    print("Engine:", engine)
    print("From:", fr)
    print("To:", to)
    print("Text:", text)
    print("E-Text:", escaped_text)

    engine_text_google = f"=> /google/{fr}/{to}/{escaped_text} "
    engine_text_libre = f"=> /libre/{fr}/{to}/{escaped_text} "
    if engine == "google":
        engine_text_google += "+ Google"
        engine_text_libre += "Libre"
    elif engine == "libre":
        engine_text_google += "Google"
        engine_text_libre += "+ Libre"

    translate = False
    translate_line = f"=> /set_text/{engine}/{fr}/{to} "
    if not text.strip(): # Check if text is empty
        translate_line += "Enter Text to Translate"
    else:
        translate_line += text
        translate = True

    lines = [
        page_header,
        "",
        "# Simply Translate",
        "",
        "Translation Engine:",
        engine_text_google,
        engine_text_libre,
        "",
        "Languages:",
        f"=> /set/from/{engine}/{to}/{escaped_text} From: {fr}",
        f"=> /set/to/{engine}/{fr}/{escaped_text} To: {to}",
        "",
        "Text:",
        translate_line,
    ]

    if translate:
        if engine == "google":
            supported_languages = googletranslate.supported_languages
            translation = googletranslate.translate(
                text,
                to_language=to_lang_code(to, supported_languages),
                from_language=to_lang_code(fr, supported_languages),
            )
        elif engine == "libre":
            supported_languages = libretranslate.supported_languages
            translation = libretranslate.translate(
                text,
                to_language=to_lang_code(to, supported_languages),
                from_language=to_lang_code(fr, supported_languages),
            )
        lines.append(translation)


    body = '\n'.join(lines)
    return Response(Status.SUCCESS, "text/gemini", body)


@app.route("/set/(?P<what>from|to)/(?P<engine>\S+)/(?P<other>\S+)", strict_trailing_slash=False)
@app.route("/set/(?P<what>from|to)/(?P<engine>\S+)/(?P<other>\S+)/(?P<text>.*)")
def set(request, what, engine, other, text=""):

    if request.query:
        lang = request.query
        #TODO check if lang is available
        if what == "from":
            return Response(Status.REDIRECT_TEMPORARY, f"/{engine}/{lang}/{other}/{text}/")
        elif what == "to":
            return Response(Status.REDIRECT_TEMPORARY, f"/{engine}/{other}/{lang}/{text}/")
    else:
        return Response(Status.INPUT, "Enter the language (either language code or full name)")

@app.route("/set_text/(?P<engine>\S+)/(?P<fr>\S+)/(?P<to>\S+)")
def set_text(request, engine, fr, to):
    print("to:", to)
    if request.query:
        text = request.query
        print("Set the text to")
        print(text)
        print(f"Redirect to /{engine}/{fr}/{to}/{text}")
        return Response(Status.REDIRECT_TEMPORARY, f"/{engine}/{fr}/{to}/{text}")
    return Response(Status.INPUT, "Enter the text you want to translate")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Gemini frontend for SimplyNews')
    parser.add_argument('hostname', default='localhost', metavar='HOSTNAME', type=str)
    parser.add_argument('port', default=1956, metavar='PORT', type=int)

    args = parser.parse_args()
    server = GeminiServer(app, port=args.port, hostname=args.hostname)
    server.run()
