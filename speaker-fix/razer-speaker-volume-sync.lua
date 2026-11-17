-- Razer Blade 16 internal speakers: push the saved volume into the speaker
-- filter graph (52-razer-speaker-volume.conf) when the speaker output first
-- starts playing.
--
-- PipeWire builds the filter graph when the output first runs, and the graph's
-- volume control starts at 0 (the bottom of the curve) until the volume next
-- changes. This happens at login, after a WirePlumber restart, and when the
-- speaker output comes back after headphones are unplugged. Here the route's
-- volume is set to a hair below its value and back, which makes PipeWire pass
-- it to the graph. The saved volume itself is not changed.

cutils = require ("common-utils")
log = Log.open_topic ("s-razer-speaker-volume")

synced = {}

function setRouteVolumes (device, route, vols)
  local arr = { "Spa:Float" }
  for _, v in ipairs (vols) do table.insert (arr, v) end
  device:set_param ("Route", Pod.Object {
    "Spa:Pod:Object:Param:Route", "Route",
    index = route.index,
    device = route.device,
    props = Pod.Object {
      "Spa:Pod:Object:Param:Props", "Route",
      channelVolumes = Pod.Array (arr),
    },
    save = false,
  })
end

function resync (device_om, dev_id, cpd)
  local device = device_om:lookup {
    Constraint { "bound-id", "=", dev_id, type = "gobject" } }
  if not device then
    log:warning ("device " .. tostring (dev_id) .. " not found")
    return
  end
  for p in device:iterate_params ("Route") do
    local route = cutils.parseParam (p, "Route")
    if route and route.direction == "Output" and route.device == cpd then
      local props = route.props and route.props.properties
      local vols = props and props.channelVolumes
      if not vols or #vols == 0 then return end
      local nudged = {}
      for i, v in ipairs (vols) do nudged [i] = v * 0.99 end
      setRouteVolumes (device, route, nudged)
      setRouteVolumes (device, route, vols)
      log:info (device, "re-applied speaker volume " .. tostring (vols [1]))
      return
    end
  end
end

SimpleEventHook {
  name = "custom/razer-speaker-volume-sync",
  interests = {
    EventInterest {
      Constraint { "event.type", "=", "node-state-changed" },
      Constraint { "node.name", "matches", "alsa_output.*HiFi__Speaker__sink" },
    },
  },
  execute = function (event)
    local node = event:get_subject ()
    local new_state = event:get_properties () ["event.subject.new-state"]
    local id = node ["bound-id"]
    if new_state ~= "running" or synced [id] then
      return
    end
    synced [id] = true
    local dev_id = tonumber (node.properties ["device.id"])
    local cpd = tonumber (node.properties ["card.profile.device"])
    local device_om = event:get_source ():call ("get-object-manager", "device")
    -- give the graph a moment to be set up
    Core.timeout_add (50, function ()
      resync (device_om, dev_id, cpd)
      return false
    end)
  end
}:register ()

-- forget nodes that went away, so a re-created speaker output is synced again
SimpleEventHook {
  name = "custom/razer-speaker-volume-sync-removed",
  interests = {
    EventInterest {
      Constraint { "event.type", "=", "node-removed" },
      Constraint { "node.name", "matches", "alsa_output.*HiFi__Speaker__sink" },
    },
  },
  execute = function (event)
    synced [event:get_subject () ["bound-id"]] = nil
  end
}:register ()
