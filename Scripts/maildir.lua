-- PalMaildir core — atomic drop into maildir/new/ (no cross-writer locking).
local config = require("config")

local M = {}

local seq = 0

local function safe(fn, fallback)
    local ok, result = pcall(fn)
    if ok then return result end
    return fallback
end

function M.root_path()
    if type(config.root_path) == "string" and config.root_path ~= "" then
        return config.root_path:gsub("/", "\\")
    end
    local root = os.getenv("LOCALAPPDATA")
    if root == nil or root == "" then
        return "PalMaildir"
    end
    return root .. "\\Pal\\Saved\\PalMaildir"
end

function M.new_dir()
    return M.root_path() .. "\\new"
end

local new_dir_ensured = false

local function ensure_new_dir()
    if new_dir_ensured then
        return true
    end
    local dir = M.new_dir()
    -- Windows: create once so io.open can write (Lua has no portable mkdir).
    os.execute('if not exist "' .. dir .. '" mkdir "' .. dir .. '"')
    new_dir_ensured = true
    return true
end

local function json_escape(s)
    s = tostring(s or "")
    s = s:gsub("\\", "\\\\")
    s = s:gsub('"', '\\"')
    s = s:gsub("\r", "\\r")
    s = s:gsub("\n", "\\n")
    return s
end

local function new_id()
    seq = seq + 1
    return string.format("%x-%06x-%04x", os.time(), seq, math.random(0, 0xffff))
end

local function new_filename()
    seq = seq + 1
    return string.format("%010d_%06x.json", os.time(), seq + math.random(0, 0xffffff))
end

local function encode_payload(payload)
    if payload == nil then
        return "{}"
    end
    if type(payload) ~= "table" then
        return "{}"
    end
    local parts = {}
    for key, value in pairs(payload) do
        if type(key) == "string" and type(value) == "string" then
            parts[#parts + 1] = string.format('"%s":"%s"', json_escape(key), json_escape(value))
        elseif type(key) == "string" and type(value) == "number" then
            parts[#parts + 1] = string.format('"%s":%s', json_escape(key), tostring(value))
        elseif type(key) == "string" and type(value) == "boolean" then
            parts[#parts + 1] = string.format('"%s":%s', json_escape(key), value and "true" or "false")
        end
    end
    return "{" .. table.concat(parts, ",") .. "}"
end

function M.publish(event)
    if type(event) ~= "table" then
        return nil, "event must be a table"
    end

    local source = event.source
    local event_type = event.type
    if type(source) ~= "string" or source == "" then
        return nil, "event.source required"
    end
    if type(event_type) ~= "string" or event_type == "" then
        return nil, "event.type required"
    end

    local title = event.title or ""
    local message = event.message or ""
    if type(title) ~= "string" then title = tostring(title) end
    if type(message) ~= "string" then message = tostring(message) end

    local id = new_id()
    local ts = os.date("!%Y-%m-%dT%H:%M:%SZ")
    local schema = tonumber(config.schema_version) or 1
    local body = string.format(
        '{"schema":%d,"id":"%s","ts":"%s","source":"%s","type":"%s","title":"%s","message":"%s","payload":%s}',
        schema,
        json_escape(id),
        json_escape(ts),
        json_escape(source),
        json_escape(event_type),
        json_escape(title),
        json_escape(message),
        encode_payload(event.payload)
    )

    ensure_new_dir()
    local dir = M.new_dir()
    local name = new_filename()
    local final_path = dir .. "\\" .. name
    local tmp_path = final_path .. ".tmp"

    local ok, err = pcall(function()
        local out = io.open(tmp_path, "w")
        if not out then
            error("io.open failed (create " .. dir .. " if missing)")
        end
        out:write(body)
        out:close()
        os.remove(final_path)
        os.rename(tmp_path, final_path)
    end)

    if not ok then
        return nil, tostring(err)
    end

    if config.debug then
        print("[PalMaildir] drop " .. final_path .. "\n")
    end

    return id, nil
end

return M
