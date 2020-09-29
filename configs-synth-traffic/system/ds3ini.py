import configparser

def init_ds3(mem_type, num_chnls):
    config = configparser.ConfigParser()
    input = 'configs-synth-traffic/ds3_configs/' \
            + mem_type + '.ini'
    output = 'configs-synth-traffic/ds3_configs/mods/' \
            + mem_type + '_' + str(num_chnls) + 'chnls.ini'
    new_config = open(output, 'w')
    config.read(input)
    config.set('system', 'channels', str(num_chnls))
    config.write(new_config)
    new_config.close()
    return output