from jetforce import GeminiServer, JetforceApplication, Response, Status
from simplytranslate_engines import (googletranslate, libretranslate)
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
Message the devs on our IRC (#simple-web on freenode)
=> https://git.sr.ht/~metalune/simplytranslate_gemini Source code for this gemini capsule
"""

app = JetforceApplication()

def get_supported_languages(engine):
    if engine == "google":
        return googletranslate.supported_languages
    elif engine == "libre":
        return libretranslate.supported_languages


def to_lang_code(lang, supported_languages):
    if lang == "Autodetect" or lang == "auto":
        return "auto"

    for key in supported_languages.keys():  
        if key.lower() == lang.lower():
            return supported_languages[key]

    for value in supported_languages.values():
        if value.lower() == lang.lower():
            return value

    return None

def to_lang_name(code, supported_languages):
    if code == "auto":
        return "Autodetect"

    for key in supported_languages.keys():
        if supported_languages[key] == code:
            return key
        
    return None





@app.route("")
@app.route("/(?P<engine>google|libre)")
@app.route("/(?P<engine>google|libre)/(?P<rest>.*)")
def index(request, engine="google", rest=""):
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


    escaped_text = urllib.parse.quote(text)
    supported_languages = get_supported_languages(engine)
    fr_name = to_lang_name(fr, supported_languages)
    to_name = to_lang_name(to, supported_languages)

    if fr_name == None or to_name == None:
        not_found = ""
        if fr_name == None:
            not_found += f"'{fr}'"
        if to_name == None:
            not_found += f" and '{to}'"
        return Response(Status.NOT_FOUND, f"Could not find {not_found}")
    
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
        f"=> /supported_languages/{engine} List of supported languages",
        "",
        "Languages:",
        f"=> /set/from/{engine}/{to}/{escaped_text} From: {fr_name}",
        f"=> /set/to/{engine}/{fr}/{escaped_text} To: {to_name}",
        "",
        "Text:",
        translate_line,
    ]

    if translate:
        if engine == "google":
            translation = googletranslate.translate(
                text,
                to_language=to,
                from_language=fr,
            )
        elif engine == "libre":
            translation = libretranslate.translate(
                text,
                to_language=to,
                from_language=fr,
            )
        lines.append("")
        lines.append("Translation:")
        lines.append(translation)


    lines.append(page_footer)
    return Response(Status.SUCCESS, "text/gemini", '\n'.join(lines))


@app.route("/set/(?P<what>from|to)/(?P<engine>\S+)/(?P<other>\S+)", strict_trailing_slash=False)
@app.route("/set/(?P<what>from|to)/(?P<engine>\S+)/(?P<other>\S+)/(?P<text>.*)")
def set(request, what, engine, other, text=""):

    if request.query:
        lang = request.query

        # check if the language is available
        lang_code = to_lang_code(lang, get_supported_languages(engine))
        if lang_code == None:
            return Response(Status.INPUT, f"Language '{lang}' not found, please try again") 

        if what == "from":
            return Response(Status.REDIRECT_TEMPORARY, f"/{engine}/{lang_code}/{other}/{text}/")
        elif what == "to":
            return Response(Status.REDIRECT_TEMPORARY, f"/{engine}/{other}/{lang_code}/{text}/")

    return Response(Status.INPUT, "Enter the language (either language code or full name)")

@app.route("/set_text/(?P<engine>\S+)/(?P<fr>\S+)/(?P<to>\S+)")
def set_text(request, engine, fr, to):
    print("to:", to)
    if request.query:
        text = request.query
        return Response(Status.REDIRECT_TEMPORARY, f"/{engine}/{fr}/{to}/{text}")

    return Response(Status.INPUT, "Enter the text you want to translate")

@app.route("/supported_languages/(?P<engine>google|libre)")
def show_supported_languages(request, engine):
    supported_languages = get_supported_languages(engine)
    lines = [
        page_header,
        "",
        f"# Supported languages for {engine}",
        "",
    ]

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
