@load policy/tuning/json-logs.zeek
@load ./scripts/hospital_detect.zeek

redef LogAscii::use_json = T;
redef Log::default_logdir = "/usr/local/zeek/logs/current";
