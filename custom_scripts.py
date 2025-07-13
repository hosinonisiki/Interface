def upload_parameter_4SLA_IIR(instrument, mim):
    filepath = '4SLA_IIR_parameters.txt'
    f = open(filepath, 'r')
    a = []
    for i in range(17):
        if i % 4 == 0 and i != 0:
            a.append(int(f.readline().strip()))
        else:
            f.readline()  # skip the line
    b = []
    for i in range(17):
        b.append(int(f.readline().strip()))
    f.close()
    for i in range(4):
        mim.get_instrument(instrument).set_parameter("memory_address", i + 17)
        mim.get_instrument(instrument).set_parameter("memory_data_high", a[i] // (2 ** 32))
        mim.get_instrument(instrument).set_parameter("memory_data_low", a[i] % (2 ** 32))
        mim.upload_control(instrument)
        mim.get_instrument(instrument).set_parameter("write_enable", 1)
        mim.upload_control(instrument)
        mim.get_instrument(instrument).set_parameter("write_enable", 0)
        mim.upload_control(instrument)
    for i in range(17):
        mim.get_instrument(instrument).set_parameter("memory_address", i)
        mim.get_instrument(instrument).set_parameter("memory_data_high", b[i] // (2 ** 32))
        mim.get_instrument(instrument).set_parameter("memory_data_low", b[i] % (2 ** 32))
        mim.upload_control(instrument)
        mim.get_instrument(instrument).set_parameter("write_enable", 1)
        mim.upload_control(instrument)
        mim.get_instrument(instrument).set_parameter("write_enable", 0)
        mim.upload_control(instrument)
    return