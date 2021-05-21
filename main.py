from jetforce import GeminiServer, JetforceApplication, Response, Status
from simplytranslate_engines.googletranslate import GoogleTranslateEngine
from simplytranslate_engines.libretranslate import LibreTranslateEngine
import urllib.parse

page_header = """```
   _____            __    ______                  __     __     
  / __(_)_ _  ___  / /_ _/_  __/______ ____  ___ / /__ _/ /____ 
 _\ \/ /  ' \/ _ \/ / // // / / __/ _ `/ _ \(_-</ / _ `/ __/ -_)
/___/_/_/_/_/ .__/_/\_, //_/ /_/  \_,_/_//_/___/_/\_,_/\__/\__/ 
           /_/     /___/                                        
```"""

page_footer = """

SimplyTranslate is part of the Simple Web project.
Message the devs on our IRC (#simple-web on irc.libera.chat)
=> https://git.sr.ht/~metalune/simplytranslate_gemini Source code for this gemini capsule
"""

google_translate_engine = GoogleTranslateEngine()

engines = [google_translate_engine, LibreTranslateEngine()]

app = JetforceApplication()

def to_lang_code(lang, engine):
    if lang == "Autodetect" or lang == "auto":
        return "auto"

    supported_languages = engine.get_supported_languages()

    for key in supported_languages.keys():  
        if key.lower() == lang.lower():
            return supported_languages[key]

    for value in supported_languages.values():
        if value.lower() == lang.lower():
            return value

    return None

def to_lang_name(code, engine):
    if code == "auto":
        return "Autodetect"

    supported_languages = engine.get_supported_languages()

    for key in supported_languages.keys():
        if supported_languages[key] == code:
            return key
        
    return None



def get_engine(engine_name):
    return next((engine for engine in engines if engine.name == engine_name), google_translate_engine)

@app.route("")
@app.route("/(?P<engine_name>google|libre)")
@app.route("/(?P<engine_name>google|libre)/(?P<rest>.*)")
def index(request, engine_name="google", rest=""):
    fr = "auto"
    to = "en"
    text = ""
    # you may ask yourself, why, why did I do it like this, well, because
    # jetforce seems to have a bug in the route system, and this just seems easier to handle for me
    rest = rest.split("/")
    if len(rest) > 0 and rest[0].strip():
        fr = rest[0]
        if len(rest) > 1:
            to = rest[1]
            if len(rest) > 2:
                text = "/".join(rest[2:])

    engine = get_engine(engine_name)

    escaped_text = urllib.parse.quote(text)
    supported_languages = engine.get_supported_languages()
    fr_name = to_lang_name(fr, engine)
    to_name = to_lang_name(to, engine)

    if fr_name == None or to_name == None:
        not_found = ""
        if fr_name == None:
            not_found += f"'{fr}'"
        if to_name == None:
            not_found += f" and '{to}'"
        return Response(Status.NOT_FOUND, f"Could not find {not_found}")

    engine_text_google = f"=> /google/{fr}/{to}/{escaped_text} "
    engine_text_libre = f"=> /libre/{fr}/{to}/{escaped_text} "
    if engine_name == "google":
        engine_text_google += "+ Google"
        engine_text_libre += "Libre"
    elif engine_name == "libre":
        engine_text_google += "Google"
        engine_text_libre += "+ Libre"

    translate = False
    translate_line = f"=> /set_text/{engine_name}/{fr}/{to} "
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
        f"=> /supported_languages/{engine_name} List of supported languages",
        "",
        "Languages:",
        f"=> /set/from/{engine_name}/{to}/{escaped_text} From: {fr_name}",
        f"=> /set/to/{engine_name}/{fr}/{escaped_text} To: {to_name}",
        "",
        "Text:",
        translate_line,
    ]

    if translate:
        lines.append("")
        lines.append("Translation:")
        lines.append(
            engine.translate(
                text,
                to_language=to,
                from_language=fr,
            )
        )


    lines.append(page_footer)
    return Response(Status.SUCCESS, "text/gemini", '\n'.join(lines))


@app.route("/set/(?P<what>from|to)/(?P<engine_name>\S+)/(?P<other>\S+)", strict_trailing_slash=False)
@app.route("/set/(?P<what>from|to)/(?P<engine_name>\S+)/(?P<other>\S+)/(?P<text>.*)")
def set(request, what, engine_name, other, text=""):
    engine = get_engine(engine_name)

    if request.query:
        lang = request.query

        # check if the language is available
        lang_code = to_lang_code(lang, engine)
        if lang_code == None:
            return Response(Status.INPUT, f"Language '{lang}' not found, please try again") 

        if what == "from":
            return Response(Status.REDIRECT_TEMPORARY, f"/{engine_name}/{lang_code}/{other}/{text}/")
        elif what == "to":
            return Response(Status.REDIRECT_TEMPORARY, f"/{engine_name}/{other}/{lang_code}/{text}/")

    return Response(Status.INPUT, "Enter the language (either language code or full name)")

@app.route("/set_text/(?P<engine_name>\S+)/(?P<fr>\S+)/(?P<to>\S+)")
def set_text(request, engine_name, fr, to):
    print("to:", to)
    if request.query:
        text = request.query
        return Response(Status.REDIRECT_TEMPORARY, f"/{engine_name}/{fr}/{to}/{text}")

    return Response(Status.INPUT, "Enter the text you want to translate")

@app.route("/supported_languages/(?P<engine_name>google|libre)")
def show_supported_languages(request, engine_name):
    engine = get_engine(engine_name)

    lines = [
        page_header,
        "",
        f"# Supported languages for {engine_name}",
        "",
    ]

    supported_languages = engine.get_supported_languages()

    for key in supported_languages.keys():
        code = supported_languages[key]
        lines.append(f"{code}: {key}")

    return Response(Status.SUCCESS, 'text/gemini', '\n'.join(lines))


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Gemini frontend for SimplyNews')
    parser.add_argument('hostname', default='localhost', metavar='HOSTNAME', type=str)
    parser.add_argument('port', default=1956, metavar='PORT', type=int)

    args = parser.parse_args()
    server = GeminiServer(app, port=args.port, hostname=args.hostname)
    server.run()
