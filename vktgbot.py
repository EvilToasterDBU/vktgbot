#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Made by @alcortazzo
v0.5
'''

import time
import urllib
import config
import requests
import eventlet
from datetime import datetime
from telebot import TeleBot, types

bot = TeleBot(config.tgBotToken)


def getData():
    timeout = eventlet.Timeout(20)
    # trying to request data from vk_api
    try:
        data = requests.get('https://api.vk.com/method/wall.get',
                            params={'access_token': config.vkToken,
                                    'v': config.reqVer,
                                    'domain': config.vkDomain,
                                    'filter': config.reqFilter,
                                    'count': config.reqCount})
        return data.json()['response']['items']
    except eventlet.timeout.Timeout:
        print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
              '| [ERROR] Got Timeout while retrieving VK JSON data. Cancelling...')
        return None
    finally:
        timeout.cancel()


def sendPosts(items, last_id):
    for item in items:
        isTypePost = 'post'
        # compares id of the last post and id from the file last_known_id.txt
        if item['id'] <= last_id:
            break
        #post = item
        # trying to check vk post type
        try:
            if item['attachments'][0]['type'] == 'photo':
                isTypePost = 'photo'
                photos = item['attachments']
                urlsPhoto = []
                # check the size of the photo and add this photo to the URL list
                # (from large to smaller)
                # photo with type W > Z > Y
                for photo in photos:
                    urls = photo['photo']['sizes']
                    if urls[-1]['type'] == 'y':
                        urlsPhoto.append(urls[-1]['url'])
                    elif urls[-1]['type'] != 'y':
                        for url in urls:
                            if url['type'] == 'w':
                                urlsPhoto.append(url['url'])
                                break
                            elif url['type'] == 'z':
                                urlsPhoto.append(url['url'])
                                break
        except Exception as ex:
            print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                  '| [Bot] [Info] Photos from the post has been added to the message',
                  'or the post did not have photos {!s} in sendPosts(): {!s}'.format(
                      type(ex).__name__, str(ex)))

        try:
            if item['attachments'][0]['type'] == 'video':
                isTypePost = 'video'
                videoUrlPreview = item['attachments'][0]['video']['image'][-1]['url']
                print(videoUrlPreview)
        except Exception as ex:
            print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                  '| [Bot] [Info] The post did not have videos {!s} in sendPosts(): {!s}'.format(
                      type(ex).__name__, str(ex)))

        try:
            if item['attachments'][0]['type'] == 'link':
                isTypePost = 'link'
                linkurl = item['attachments'][0]['link']['url']
                print(linkurl)
        except Exception as ex:
            print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                  '| [Bot] [Info] The post did not have links {!s} in sendPosts(): {!s}'.format(
                      type(ex).__name__, str(ex)))

        # send message according to post type
        if isTypePost == 'post':
            bot.send_message(config.tgChannel, item['text'])
            print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"), '| [Bot] Text post without photo/video sent')

        elif isTypePost == 'photo':
            listOfPhotos = []
            # get photos from urls
            for urlPhoto in urlsPhoto:
                listOfPhotos.append(types.InputMediaPhoto(urllib.request.urlopen(urlPhoto).read()))
            # send messages with photos
            bot.send_message(config.tgChannel, item['text'])
            bot.send_media_group(config.tgChannel, listOfPhotos)
            print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"), '| [Bot] Text post with photos sent')

        elif isTypePost == 'video':
            # get preview from youtube video
            listOfPreviews = []
            listOfPreviews.append(types.InputMediaPhoto(urllib.request.urlopen(videoUrlPreview).read()))
            # send messages with video preview
            bot.send_message(config.tgChannel, item['text'])
            bot.send_media_group(config.tgChannel, listOfPreviews)
            print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"), '| [Bot] Text post with video preview sent')

        elif isTypePost == 'link':
            tgPost = '{!s}{!s}'.format(item['text'], '\n\n' + linkurl)
            bot.send_message(config.tgChannel, tgPost)
            print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"), '| [Bot] Text post with links sent')


def checkNewPost():
    print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"), '| [VK] Started scanning for new posts')
    with open('last_known_id.txt', 'r') as file:
        last_id = int(file.read())
        if last_id is None:
            print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                  '| [ERROR] Could not read from storage. Skipped iteration')
            return
        print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"), '| [Info] Last id of vk post is {!s}'.format(last_id))
    try:
        feed = getData()
        # continue if we received data
        if feed is not None:
            entries = feed
            try:
                # if the post is pinned, skip it
                pinned = entries[0]['is_pinned']
                # and call sendPosts
                config.isPinned = True
                sendPosts(entries[1:], last_id)
            except KeyError:
                config.isPinned = False
                sendPosts(entries, last_id)
            # write new last_id to file
            with open('last_known_id.txt', 'w') as file:
                try:
                    pinned = entries[0]['is_pinned']
                    file.write(str(entries[1]['id']))
                    print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                          '| [Info] New Last id (VK) is {!s}'.format((entries[1]['id'])))
                except KeyError:
                    file.write(str(entries[0]['id']))
                    print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
                          '| [Info] New Last id (VK) is {!s}'.format((entries[0]['id'])))
    except Exception as ex:
        print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
              '| Excepion in type {!s} in checkNewPost(): {!s}'.format(type(ex).__name__, str(ex)))
        pass
    print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"), '| [VK] Finished scanning')
    return


if __name__ == '__main__':
    if not config.singleStart:
        while True:
            checkNewPost()
            print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"), '| [Bot] Script went to sleep for', config.timeSleep,
                  'seconds\n\n')
            # pause for n minutes (timeSleep in config.py)
            time.sleep(int(config.timeSleep))
    elif config.singleStart:
        checkNewPost()
        print(datetime.now().strftime("%d-%m-%Y %H:%M:%S"), '| [Bot] Script exited.\n')
