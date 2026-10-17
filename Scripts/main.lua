-- PalMaildir — shared maildir bus for UE4SS mods (publish only; external watcher consumes new/).
local config = require("config")
local maildir = require("maildir")

local MOD = "[PalMaildir]"
local VERSION = "1.0.0"

local function log(msg)
    print(MOD .. " " .. msg .. "\n")
end

local API = {
    VERSION = VERSION,
    SCHEMA = tonumber(config.schema_version) or 1,
    root_path = maildir.root_path,
    new_dir = maildir.new_dir,
    publish = maildir.publish,
}

_G.PalMaildir = API
_G.__PALMAILDIR = API

log("v" .. VERSION .. " library ready; new=" .. maildir.new_dir())
log("Other mods: _G.PalMaildir.publish({ source, type, title?, message?, payload? })")
