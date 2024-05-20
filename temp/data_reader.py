
if __name__ == "__main__":
    from .kuka import KUKA_Handler, KUKA_DataReader

    import traceback
    from progress.bar import Bar
    
    h = KUKA_Handler("192.168.1.152", 7000)
    
    if not h.KUKA_Open():
        exit(1)

    collection = KUKA_DataReader(h)
    collection.READ_TQ[1:7] = True
    collection.READ_TEMP[1:7] = True
    collection.READ_CURR[1:7] = True
    collection.READ_POS_ACT = True
    collection.READ_POS_MEAS = True

    try:
        print(collection._data_available,collection._read_done)
        print(collection.ColRUN)
        print(collection.READ_TQ[1:7])
        print(collection.READ_TEMP[1:7])
        print(collection.READ_CURR[1:7])
        print(collection.READ_POS_ACT)
        print(collection.READ_POS_MEAS)

        print(collection.handler.KUKA_ReadVar("__TAB_1[]"))
    
        # print("Waiting to collect ...")
        # with Bar("Collection ...", max=20000) as bar:
        #     data = collection.run(lambda: bar.next())
        
    except Exception as e:
        traceback.print_exception(e)


    h.KUKA_Close()