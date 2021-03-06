import requests
import ast
import os
import inspect
from lxml import etree
from sys import stdin

url = "http://live.afreeca.com:8057/afreeca/broad_list_api.php"
NICKNAME_ = 0
_connect_timeout = 8
_read_timeout = 4

def print_msg(message):
    print(message)

print_dbg_global = print_msg

def print_dbg(message):
    print_dbg_global(inspect.stack()[1][3] + ": " + message)

def init(msg_function, dbg_function):
    global print_msg
    global print_dbg
    
    # changing print functions
    print_msg = msg_function
    print_dbg_global = dbg_function


def print_online_list(online_BJs, message="streamers online: ", verbose=False):
    if not verbose:
        print_msg(message + ", ".join( \
                  streamer["nickname"] +
                  (" (password)" if streamer["is_password"] != "N" else "") +
                  (" (vods)" if "[재]" in streamer["broad_title"] else "") \
                  for streamer in online_BJs))
    else:
        # sort by date
        print_msg("streamers online: " + ", ".join( \
                  streamer["nickname"] + " " +
                  streamer["broad_start"][-5:] + "KST " +
                  streamer["total_view_cnt"] + "v" +
                  (" (password)" if streamer["is_password"] != "N" else "") +
                  (" (vods)" if "[재]" in streamer["broad_title"] else "") \
                  for streamer in online_BJs))
        #print("players online: " + ", ".join(player["nickname"] + " " + player["total_view_cnt"] for player in online_BJs))


def get_online_BJs(afreeca_database, verbose=False, quiet=False, tune_oom=False, broadlist_filename=None):
    if tune_oom:
        # tuning linux oom killer for current process for high chance to kill it,
        # as ast.literal_eval parsing process consumes a lot of memory 500+ megobytes of RAM
        with open("/proc/%d/oom_adj" % os.getpid(), 'w') as hF:
            print("%d" % 14, file=hF)
    
    print_msg("fetching online streamers list...")

    if broadlist_filename is not None:
        with open(broadlist_filename, 'r', encoding='EUC-KR', errors='ignore') as hF:
            string = hF.read()
            parsed = ast.literal_eval(string[21:-1])
    else:
        try:
            r = requests.get(url, timeout = (_connect_timeout, _read_timeout))
        except Exception as x:
            print_dbg("Request failed: " + str(x))
            return -1
        
        try:
            parsed = ast.literal_eval(r.text[21:-1])
        except Exception as x:
            print_dbg("Failed to parse BroadListData: " + str(x))
            return -1
    
    online_BJs = []
    
    afreeca_database_fset = frozenset(afreeca_database.keys()) # maybe for better lookup performance
    for bj in parsed["CHANNEL"]["REAL_BROAD"]:
        if bj["user_id"] in afreeca_database_fset and \
        bj["broad_cate_no"] == "00040001":
            player_info = \
            {   "nickname": afreeca_database[bj["user_id"]][NICKNAME_]
            ,   "total_view_cnt": bj["total_view_cnt"]
            ,   "is_password": bj["is_password"]
            ,   "broad_title": bj["broad_title"]
            ,   "broad_start": bj["broad_start"]
            ,   "rank": bj["rank"]
            }
            online_BJs.append(player_info)
            #print_dbg(bj["user_id"] + " total:" + bj["total_view_cnt"] + " pc:" + bj["pc_view_cnt"] + " mobile:" + bj["m_current_view_cnt"])
    
    # sorting by afreeca rank
    online_BJs = sorted(online_BJs, key=lambda s: int(s["rank"]))
    
    # sorting by password existence
    online_BJs = sorted(online_BJs, key=lambda s: s["is_password"] != "N")
    
    # sorting streams with vods to end of list
    online_BJs = sorted(online_BJs, key=lambda s: ("[재]" in s["broad_title"]))
    
    #print_dbg("players online: " + ", ".join(player["nickname"] + " " + player["rank"] for player in online_BJs))
        
    if not quiet:
        print_online_list(online_BJs, verbose=verbose)
    
    #return frozenset(list(player["nickname"] for player in online_BJs)) # frozenset(list(..)) remains the order
    #return list(player["nickname"] for player in online_BJs) # frozenset(list(..)) remains the order
    return online_BJs


def isbjon(afreeca_id, quiet=False):
    try:
        xml_tree = etree.parse( "http://afbbs.afreeca.com:8080/api/video/get_bj_liveinfo.php?szBjId=" + \
                                afreeca_id )
        result = xml_tree.find("result").text
    except Exception as x:
        print_dbg("warning, improper response from afreeca about broadcast jockey online status: " + str(x))
        return -1
    
    if not quiet:
        #print_msg(afreeca_id + " is " + ( "online (%s pc viewers, i.e. excluding mobile viewers)" % xml_tree.find("view_cnt").text
                                          #if result == '1' else "offline" ))
        #print_msg(afreeca_id + " is " + ( "online (%s viewers)" % xml_tree.find("view_cnt").text
                                          #if result == '1' else "offline" ))
        print_msg(afreeca_id + " is " + ( "online (%s viewers at main room)" % xml_tree.find("view_cnt").text
                                          if result == '1' else "offline" ))
    
    return True if result == '1' else False
