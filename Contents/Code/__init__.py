# PMS plugin framework
from PMS import *
from PMS.Objects import *
from PMS.Shortcuts import *
from BeautifulSoup import BeautifulStoneSoup as BSS

import re

####################################################################################################

APPLICATIONS_PREFIX = "/applications/boardgamegeek"

NAME = L('Title')

API_URL = 'http://boardgamegeek.com/xmlapi/%s'

# make sure to replace artwork with what you want
# these filenames reference the example files in
# the Contents/Resources/ folder in the bundle
ART           = 'art-default.png'
ICON          = 'icon-default.png'

####################################################################################################

def Start():
    Plugin.AddPrefixHandler(APPLICATIONS_PREFIX, ApplicationsMainMenu, L('ApplicationsTitle'), ICON, ART)

    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    Plugin.AddViewGroup("List", viewMode="List", mediaType="items")

    MediaContainer.art = R(ART)
    MediaContainer.title1 = NAME
    DirectoryItem.thumb = R(ICON)

def CreatePrefs():
    Prefs.Add(id='username', type='text', default='', label='Your Username')
    # Prefs.Add(id='password', type='text', default='', label='Your Password', option='hidden')

def ValidatePrefs():
    u = Prefs.Get('username')
    # p = Prefs.Get('password')
    ## do some checks and return a
    ## message container
    if( u ):
        return MessageContainer(
            "Success",
            "User and password provided ok"
        )
    # else:
    #     return MessageContainer(
    #         "Error",
    #         "You need to provide both a user and password"
    #     )


def ApplicationsMainMenu():
    u = Prefs.Get('username')
    dir = MediaContainer(viewGroup="InfoList")
    dir.Append(
        Function(
            PopupDirectoryItem(
                GetCollections,
                "User collections",
                subtitle="",
                summary="Show %s's BoardGameGeek collections" % u,
                thumb=R(ICON),
                art=R(ART)
            )
        )
    )
    dir.Append(
        Function(
            InputDirectoryItem(
                SearchResults,
                title="Search BoardGameGeek",
                prompt="Search board game title"
            )
        )
    )
    dir.Append(
        PrefsItem(
            "Preferences",
            summary="Set your BoardGameGeek preferences",
        )
    )
    return dir


def GetCollections(sender):   
    u = Prefs.Get('username')
    if (u):
        dir = MediaContainer(viewGroup="InfoList")
        dir.Append(
            Function(
                DirectoryItem(
                    ShowCollection,
                    title="Owned",
                    # subtitle=game.find('boardgamepublisher').text,
                    # summary=game.find('description').text,
                    # thumb=game.find('thumbnail').text,
                    art=R(ART),
                )
            )
        )
        dir.Append(
            Function(
                DirectoryItem(
                    ShowCollection,
                    title="Wishlist",
                    # subtitle=game.find('boardgamepublisher').text,
                    # summary=game.find('description').text,
                    # thumb=game.find('thumbnail').text,
                    art=R(ART),
                )
            )
        )
        return dir
    else:
        return MessageContainer(
            "No user specified",
            # "In real life, you'll make more than one callback,\nand you'll do something useful.\nsender.itemTitle=%s" % sender.itemTitle
            "A username must be specified in the preferences"
        )
    

def ShowCollection(sender):
    u = Prefs.Get('username')
    if (sender.itemTitle == "Wishlist"):
        url_params = '%s?wishlist=1' % u
    else:
        url_params = '%s?own=1' % u
    collection_xml = XML.ElementFromURL(API_URL % 'collection/%s' % url_params)
    boardgames = collection_xml.findall('item')
    return build_menu_from_xml(boardgames, "%s: %s" % (u, sender.itemTitle))
    

def SearchResults(sender,query=None):
    try:
        search_xml = XML.ElementFromURL(API_URL % 'search?search=%s' % query)
    except HTTPError, e:
        Log(e.code)
    boardgames = search_xml.findall('boardgame')
    return build_menu_from_xml(boardgames, "Search: %s" % query)

def GameDetails(sender, game_id=None):
    games_xml = XML.ElementFromURL(API_URL % 'boardgame/%s' % game_id)
    game = games_xml.find('boardgame')
    dir = MediaContainer(viewGroup="InfoList", title2=sender.itemTitle)
    summary = game.find('description').text.replace('<br/>',"\n").replace("\n\n", "\n").replace("\n\n", "\n")
    soup = BSS(summary, convertEntities=BSS.HTML_ENTITIES)
    summary = soup.contents[0]
    dir.Append(
        Function(
            DirectoryItem(
                GameDetails,
                title=sender.itemTitle,
                subtitle="Description",
                summary=summary,
                thumb=game.find('image').text
            )
        )
    )
    publishers = []
    for publisher in game.findall('boardgamepublisher'):
        publishers.append(publisher.text)
    publishers = "\n".join(publishers)
    dir.Append(
        Function(
            DirectoryItem(
                GameDetails,
                title="Publishers",
                summary=publishers,
            )
        )
    )
    return dir

def build_menu_from_xml(boardgames, title="Games"):
    games_list = []
    for game in boardgames:
        games_list.append(game.get('objectid'))
    
    games_query = ",".join(games_list)
    games_xml = XML.ElementFromURL(API_URL % 'boardgame/%s' % games_query)
    dir = MediaContainer(viewGroup="InfoList", title2=title)
    for game in games_xml:
        try:
            thumbnail=game.find('image').text
        except AttributeError, e:
            thumbnail=R(ICON)
        dir.Append(
            Function(
                DirectoryItem(
                    GameDetails,
                    title=game.find('.//name[@primary]').text,
                    summary=strip_html(game.find('description').text),
                    thumb=thumbnail
                ), game_id=game.get('objectid')
            )
        )
    return dir
    

def strip_html(text):
    def fixup(m):
        text = m.group(0)
        if text == "<br/>":
            return "\n"
        if text[:1] == "<":
            return "" # ignore tags
        if text[:2] == "&#":
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        elif text[:1] == "&":
            import htmlentitydefs
            entity = htmlentitydefs.entitydefs.get(text[1:-1])
            if entity:
                if entity[:2] == "&#":
                    try:
                        return unichr(int(entity[2:-1]))
                    except ValueError:
                        pass
                else:
                    return unicode(entity, "iso-8859-1")
        return text # leave as is
    return re.sub("(?s)<[^>]*>|&#?\w+;", fixup, text)