idx=0
while true; do
    if ffprobe -i "{}" -stimeout 10000000; then
        export IDX=$idx
        {}
    fi
    idx=$(($idx + 1))
    echo "retrying for sourceID {}"
    python3 send_alert.py {}
    sleep {}
done