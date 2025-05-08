idx=0
while true; do
    if ffprobe -i "{}"; then
        export IDX=$idx
        {}
    fi
    idx=$(($idx + 1))
    echo "retrying for sourceID {}"
    python3 send_alert.py {}
    sleep {}
done
