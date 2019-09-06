# coding=utf-8
import requests
from aiohttp import ClientSession, ClientResponse, ClientRequest
from requests import Response, Request
from apig_sdk import signer

import asyncio
import sys
import json
from socket import socket, AF_INET, SOCK_DGRAM
import argparse


Key = 'D9DWPJA0QJQERLJI3RQK'
Secret = 'YbZ488oym5tG2ZZdfMvScZee8mCRUzclwsN0opIV'
EndPoint = 'dns.cn-north-4.myhuaweicloud.com'

CONFIG = {
    "names": [
        'h.huazhang.me',
    ],
    'weight': 1,
    "description": "h"
}


class Api():
    def __init__(self, key=Key, secret=Secret, end_point=EndPoint):
        self._key = key
        self._secret = secret
        self._end_point = end_point
        self._sig = self._create_sig()

    def _create_sig(self) -> signer.Signer:
        sig = signer.Signer()
        sig.Key = self._key
        sig.Secret = self._secret
        return sig

    async def get(self, resource_name='', data='', url='', version='v2.1', **query):
        if not url:
            query_str = '&'.join(f'{k}={v}' for k, v in query.items())
            url = f'https://{self._end_point}/{version}/{resource_name}?{query_str}'
        else:
            url = f'https://{self._end_point}/{version}/{url}'
        return await self._req('GET', url, data)

    async def post(self, resource_name='', data='', url='', version='v2.1', **query):
        if not url:
            query_str = '&'.join(f'{k}={v}' for k, v in query.items())
            url = f'https://{self._end_point}/{version}/{resource_name}?{query_str}'
        else:
            url = f'https://{self._end_point}/{version}/{url}'
        return await self._req('POST', url, data)

    async def delete(self, resource_name='', data='', url='', version='v2.1', **query):
        if not url:
            query_str = '&'.join(f'{k}={v}' for k, v in query.items())
            url = f'https://{self._end_point}/{version}/{resource_name}?{query_str}'
        else:
            url = f'https://{self._end_point}/{version}/{url}'
        return await self._req('DELETE', url, data)

    async def put(self, resource_name='', data='', url='', version='v2.1', **query):
        if not url:
            query_str = '&'.join(f'{k}={v}' for k, v in query.items())
            url = f'https://{self._end_point}/{version}/{resource_name}?{query_str}'
        else:
            url = f'https://{self._end_point}/{version}/{url}'
        return await self._req('PUT', url, data)

    async def _req(self, method, url, data):
        r = signer.HttpRequest(method, url)
        r.headers = {'content-type': 'application/json'}
        if isinstance(data, dict):
            data = json.dumps(data)
        r.body = data
        self._sig.Sign(r)

        async with ClientSession() as session:
            session: ClientSession
            async with session.request(
                r.method,
                r.scheme + '://' + r.host + r.uri,
                headers=r.headers,
                data=r.body
            ) as resp:
                resp: ClientResponse
                print(resp.request_info.url)
                if resp.status < 200 or resp.status >= 300:
                    print(resp.status, resp.reason)
                    text = await resp.text()
                    print(f'error = {text}')
                return await resp.json()


async def get_ip(url='http://v4.ipv6-test.com/api/myip.php'):
    async with ClientSession() as session:
        session: ClientSession
        async with session.get(url) as resp:
            return await resp.text()


async def add_record(name, description='', weight=1):
    ip = await get_ip()
    print(ip)
    api = Api()
    data = await api.get('zones', version='v2', type='public')
    zone_id = data['zones'][0]['id']

    record_data = {
        'name': name,
        'description': description,
        'type': 'A',
        'ttl': 120,
        'weight': weight,
        'records': [
            ip
        ]
    }
    data = await api.post(url=f'zones/{zone_id}/recordsets', data=record_data)
    if not data.get('id', None):
        raise Exception('add fail')
    return data


async def del_records(**query):
    if not query:
        return
    if 'name' in query and not query['name'].endswith('.'):
        query['name'] = f'{query["name"]}.'

    api = Api()
    data = await api.get('zones', version='v2', type='public')
    zone_id = data['zones'][0]['id']

    data = await api.get('recordsets', query=query)

    records = []
    for r in data['recordsets']:
        for k, v in query.items():
            if k not in r or r[k] != v:
                break
        else:
            records.append(r)

    for r in records:
        print(f'delete {r["id"]}, {r["name"]}')
        data = await api.delete(url=f'zones/{zone_id}/recordsets/{r["id"]}')

    return


def load_config(config_path):
    with open(config_path) as fp:
        config = json.load(fp)
    return config


async def run(args):
    config = load_config(args.config)
    api = Api(key=config['key'], secret=config['secret'])
    data = await api.get('zones', version='v2', type='public')
    # print(data)

    if args.put:
        for name in config['names']:
            try:
                print(f'adding {name}')
                await add_record(name, config['description'], config['weight'])
                print(f'add success {config["description"]}')
            except Exception as e:
                print(f'error {e}')

    if args.delete:
        try:
            print(f'deleting')
            data = await del_records(description=config['description'])
            print(f'delete success {config["description"]}')
        except Exception as e:
            print(f'error {e}')

    if args.update:
        print(f'updating {config["description"]}')
        try:
            print(f'deleting {config["description"]}')
            data = await del_records(description=config['description'])
            print(f'delete success {config["description"]}')
        except Exception as e:
            print(f'error {e}')

        for name in config['names']:
            try:
                print(f'add {name}')
                await add_record(name, config['description'], config['weight'])
                print(f'add success {config["description"]}')
            except Exception as e:
                print(f'error {e}')
        print(f'update success {config["description"]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='华为云解析DDNS')
    parser.add_argument('-c', '--config', default='./config.json', help='配置文件位置')
    parser.add_argument('-delete', dest='delete', action='store_true', help='删除DNS记录, 一般关机时调用')
    parser.add_argument('-update', dest='update', action='store_true', help='更新DNS记录, 一般系统启动时调用')
    parser.add_argument('-put', dest='put', action='store_true', help='直接添加DNS记录')
    args = parser.parse_args()

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run(args))


