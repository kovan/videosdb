
ipfs filestore ls > /tmp/asdf

ls -1 /home/k/bucket/videos| while read f;
do
	if cat /tmp/asdf | grep -q "$f"
	then
		echo YES
	else
		echo NO, adding $f
		ipfs add --nocopy "/home/k/bucket/videos/$f"
	fi
done

rm /tmp/asdf
