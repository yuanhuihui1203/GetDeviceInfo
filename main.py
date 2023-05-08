import uvicorn
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import clr
import yaml, os, sys
import psutil
from starlette.responses import JSONResponse

sys.path.append(os.getcwd())

app = FastAPI(title="设备信息获取",
              description="用于获取windows下显卡，内存，cpu，网卡等使用情况",
              version="v0.1")


class GetDeviceInfo:

    def __init__(self, dll: str):

        clr.AddReference(dll)
        from LibreHardwareMonitor.Hardware import Computer  # 在编译器里 这里有可能会报错 但是可以忽略他
        self.computer_tmp = Computer()  # 实例这这个类
        self.computer_tmp.IsCpuEnabled = True  # 获取CPU温度时用
        self.computer_tmp.IsGpuEnabled = True  # 获取GPU温度时用
        self.computer_tmp.IsMemoryEnabled = True  # 获取内存时用
        # self.computer_tmp.IsNetworkEnabled = True  # 获取RAM温度时用
        self.computer_tmp.Open()

    @staticmethod
    def memory_info() -> tuple:
        p = psutil.virtual_memory()
        return p.total / 1024 / 1024, p.used / 1024 / 1024

    def params_hardware(self, index: int) -> dict:
        hard = self.computer_tmp.Hardware[index]
        hard.Update()
        device_data = {}

        for i in hard.Sensors:
            sensor_type = str(i.SensorType)
            if sensor_type == "Load" and sensor_type not in device_data:
                device_data["Name"] = hard.Name
                device_data["Load"] = i.Value
            if index == 2 and "/temperature" in str(i.Identifier):
                device_data["temperature"] = i.Value
            if sensor_type == "Load" and index == 2:
                device_data[str(i.Name).replace("D3D ", "")] = i.Value
        if index == 1:
            total, used = self.memory_info()
            device_data['total'] = total
            device_data['used'] = used
        return device_data

    def run(self):
        data_list = []
        type_list = ["CPU", "memory", "GPU"]
        com_len = len(self.computer_tmp.Hardware)
        if com_len > len(type_list):
            number = com_len - len(type_list)
            [type_list.append("other" + str(i)) for i in range(number)]
        for index in range(com_len):
            device_info = self.params_hardware(index)
            device_info['type'] = type_list[index]
            data_list.append(device_info)
        return data_list


class Router:
    routerApi = APIRouter()

    def __init__(self):
        path = os.path.dirname(sys.executable)
        self.device = GetDeviceInfo(path + "/lib/LibreHardwareMonitorLib")

    async def get_device_info(self):
        return JSONResponse(
            status_code=200,
            content={
                "message": "success!",
                "code": 200,
                "data": self.device.run()
            }
        )

    def router_list(self):
        self.routerApi.add_api_route("/deviceInfo", self.get_device_info, methods=["GET"])


def init_service():
    app.add_middleware(CORSMiddleware,
                       allow_origins="*",
                       allow_credentials=True,
                       allow_methods=["*"],
                       allow_headers=["*"], )
    router = Router()
    router.router_list()
    app.include_router(router.routerApi, prefix="/device")


init_service()
if __name__ == '__main__':
    with open("config/config.yaml", mode='r+', encoding='utf-8') as f:
        data = yaml.load(f.read(), Loader=yaml.Loader)
    uvicorn.run("__main__:app", host=data['host'], port=data['port'])
