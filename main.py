from jetforce import GeminiServer, JetforceApplication, Response, Status
from configparser import ConfigParser

from simplytranslate_engines.googletranslate import GoogleTranslateEngine
from simplytranslate_engines.libretranslate import LibreTranslateEngine
from simplytranslate_engines.utils import *

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

config = ConfigParser()

config.read(["/etc/simplytranslate/shared.conf", "/etc/simplytranslate/gemini.conf"])

engines = []

if config.getboolean('google', 'Enabled', fallback=True):
    engines.append(GoogleTranslateEngine())

libretranslate_enabled = config.getboolean('libretranslate', 'Enabled', fallback=None)

if libretranslate_enabled is None:
    print("LibreTranslate is disabled by default; if you did not mean this, please edit the config file")

if libretranslate_enabled:
    engines.append(
        LibreTranslateEngine(
            config['libretranslate']['Instance'],
            # `ApiKey` is not required, so use `get` to get `None` as fallback.
            config['libretranslate'].get('ApiKey'),
        )
    )

if not engines:
    raise Exception('All translation engines are disabled')

engine_names = tuple(engine.name for engine in engines)
joined_engine_names = "|".join(engine_names)

app = JetforceApplication()

@app.route("")
@app.route("/(?P<engine_name>{})".format(joined_engine_names))
@app.route("/(?P<engine_name>{})/(?P<rest>.*)".format(joined_engine_names))
def index(request, engine_name=engine_names[0], rest=""):
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

    engine = get_engine(engine_name, engines, engines[0])

    escaped_text = urllib.parse.quote(text)
    supported_source_languages = engine.get_supported_source_languages()
    supported_target_languages = engine.get_supported_target_languages()

    fr_name = to_full_name(fr, engine)
    to_name = to_full_name(to, engine)

    if fr_name == None or to_name == None:
        not_found = ""
        if fr_name == None:
            not_found += f"'{fr}'"
        if to_name == None:
            not_found += f" and '{to}'"
        return Response(Status.NOT_FOUND, f"Could not find {not_found}")

    engine_lines = []

    def add_engine_line(name, display_name):
        if name in engine_names:
            string = f"=> /{name}/{fr}/{to}/{escaped_text} "
            if engine_name == name:
                string += f"+ {display_name}"
            else:
                string += display_name
            engine_lines.append(string)

    add_engine_line("libre", "Libre")
    add_engine_line("google", "Google")

    # if there is only one engine, just don't explain any engine options
    if len(engine_lines) == 1:
        engine_lines = []

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
        *engine_lines,
        f"=> /supported_source_languages/{engine_name} List of supported source languages",
        f"=> /supported_target_languages/{engine_name} List of supported target languages",
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


@app.route("/set/(?P<what>from|to)/(?P<engine_name>{})/(?P<other>\S+)".format(joined_engine_names), strict_trailing_slash=False)
@app.route("/set/(?P<what>from|to)/(?P<engine_name>{})/(?P<other>\S+)/(?P<text>.*)".format(joined_engine_names))
def set(request, what, engine_name, other, text=""):
    engine = get_engine(engine_name, engines, engines[0])

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

@app.route("/set_text/(?P<engine_name>{})/(?P<fr>\S+)/(?P<to>\S+)".format(joined_engine_names))
def set_text(request, engine_name, fr, to):
    print("to:", to)
    if request.query:
        text = request.query
        return Response(Status.REDIRECT_TEMPORARY, f"/{engine_name}/{fr}/{to}/{text}")

    return Response(Status.INPUT, "Enter the text you want to translate")

@app.route("/supported_source_languages/(?P<engine_name>{})".format(joined_engine_names))
def show_supported_source_languages(request, engine_name):
    engine = get_engine(engine_name, engines, engines[0])

    lines = [
        page_header,
        "",
        f"# Supported source languages for {engine_name}",
        "",
    ]

    supported_source_languages = engine.get_supported_source_languages()

    for key in supported_source_languages.keys():
        code = supported_source_languages[key]
        lines.append(f"{code}: {key}")

    return Response(Status.SUCCESS, 'text/gemini', '\n'.join(lines))

@app.route("/supported_target_languages/(?P<engine_name>{})".format(joined_engine_names))
def show_supported_target_languages(request, engine_name):
    engine = get_engine(engine_name, engines, engines[0])

    lines = [
        page_header,
        "",
        f"# Supported target languages for {engine_name}",
        "",
    ]

    supported_target_languages = engine.get_supported_target_languages()

    for key in supported_target_languages.keys():
        code = supported_target_languages[key]
        lines.append(f"{code}: {key}")

    return Response(Status.SUCCESS, 'text/gemini', '\n'.join(lines))

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description='Gemini frontend for SimplyTranslate')
    parser.add_argument('hostname', default='localhost', metavar='HOSTNAME', type=str)
    parser.add_argument('host', default='127.0.0.1', metavar="HOST", type=str)
    parser.add_argument('port', default=1956, metavar='PORT', type=int)

    args = parser.parse_args()
    server = GeminiServer(app, port=args.port, host=args.host, hostname=args.hostname)
    server.run()
