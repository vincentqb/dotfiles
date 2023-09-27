function fish_greeting

    for motd in /run/motd.dynamic /etc/motd
        if test -e $motd
            cat $motd
        end
    end

    _pure_check_for_new_release
end
