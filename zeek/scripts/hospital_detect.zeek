module Hospital;

export {
  redef enum Notice::Type += {
    Suspicious_Radiology_Transfer,
    Medical_Device_Scan
  };
}

event connection_established(c: connection)
  {
  if ( c$id$resp_p == 104/tcp || c$id$resp_p == 502/tcp || c$id$resp_p == 1883/tcp )
    {
    NOTICE([$note=Medical_Device_Scan,
            $msg=fmt("Connection to medical device protocol port %s", c$id$resp_p),
            $conn=c]);
    }
  }

event connection_state_remove(c: connection)
  {
  if ( c$orig$size > 50000000 && c$id$resp_p == 443/tcp )
    {
    NOTICE([$note=Suspicious_Radiology_Transfer,
            $msg=fmt("Large outbound radiology-like transfer: %d bytes", c$orig$size),
            $conn=c]);
    }
  }
