-- PalEventDrop — shared event file bus for UE4SS mods (publish only; PC watcher reads pending/).
local config = require("config")
local drop = require("drop")

local MOD = "[PalEventDrop]"
local VERSION = "1.0.0"

local function log(msg)
    print(MOD .. " " .. msg .. "\n")
end

local API = {
    VERSION = VERSION,
    SCHEMA = tonumber(config.schema_version) or 1,
    root_path = drop.root_path,
    pending_dir = drop.pending_dir,
    publish = drop.publish,
}

_G.PalEventDrop = API
_G.__PALEVENTDROP = API

log("v" .. VERSION .. " library ready; pending=" .. drop.pending_dir())
log("Other mods: _G.PalEventDrop.publish({ source, type, title?, message?, payload? })")
