import math
import os
import random
import sys
import time
from typing import Any
import pygame as pg
from pygame.sprite import AbstractGroup


WIDTH = 1200  # ゲームウィンドウの幅
HEIGHT = 750  # ゲームウィンドウの高さ
GOAL = 4800
# WIDTH = 700
# HEIGHT = 500
MAIN_DIR = os.path.split(os.path.abspath(__file__))[0]
MV_FIELD = False# スクロールの許可
MV_MOVE = False # 移動の許可
FLY_COUNT = 0 # 飛翔時間のカウント


def check_bound(obj: pg.Rect) -> tuple[bool, bool]:
    """
    オブジェクトが画面内か画面外かを判定し，真理値タプルを返す
    引数 obj：オブジェクト（爆弾，こうかとん，ビーム）SurfaceのRect
    戻り値：横方向，縦方向のはみ出し判定結果（画面内：True／画面外：False）
    """
    yoko, tate = True, True
    if obj.left < 0 or WIDTH < obj.right:  # 横方向のはみ出し判定
        yoko = False
    if obj.top < 0 or HEIGHT < obj.bottom:  # 縦方向のはみ出し判定
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }

    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"{MAIN_DIR}/fig/{num}.png"), 0, 2.0)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 1.0),  # 右上
            (0, -1): img,  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 1.0),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 1.0),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 1.0),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 1.0),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10

    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"{MAIN_DIR}/fig/{num}.png"), 0, 2.0)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        global MV_FIELD,FLY_COUNT,MV_MOVE
        sum_mv = [0, 0]
        moto_center = self.rect.center
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                self.rect.move_ip(+self.speed*mv[0], +self.speed*mv[1])
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
                if k == pg.K_UP:
                    FLY_COUNT += 1
                    if 20 <= FLY_COUNT < 35:
                        self.rect.move_ip(-self.speed*mv[0], -self.speed*mv[1])
                        MV_MOVE = False
                    elif 35 <= FLY_COUNT:
                        FLY_COUNT = 0
        self.rect.move_ip(0,2)
        if check_bound(self.rect) != (True, True):
            for k, mv in __class__.delta.items():
                if key_lst[k]:
                    self.rect.move_ip(-self.speed*mv[0], -self.speed*mv[1])
                    MV_MOVE = False
        if self.rect.right > WIDTH/13*5:   #画面推移のための線引き
            self.rect.move_ip(-self.speed*mv[0],0)
            MV_FIELD = True
        if MV_MOVE == True:
            for k, mv in __class__.delta.items():
                if key_lst[k]:
                    self.rect.move_ip(-self.speed*mv[0], -self.speed*mv[1])
            self.rect.move_ip(0,10)
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        self.image = pg.Surface((2*rad, 2*rad))
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height/2
        self.speed = 6

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(+self.speed*self.vx, +self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"{MAIN_DIR}/fig/beam.png"), angle, 2.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(+self.speed*self.vx, +self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"{MAIN_DIR}/fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"{MAIN_DIR}/fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self):
        super().__init__()
        self.image = random.choice(__class__.imgs)
        self.rect = self.image.get_rect()
        self.rect.center = random.randint(0, WIDTH), 0
        self.vy = +6
        self.bound = random.randint(50, HEIGHT/2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.centery += self.vy


class Score:
    """
    敵機の数をスコアとして表示するクラス
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 0
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class Coin(pg.sprite.Sprite):
    """
    コインに関するクラス
    """
    def __init__(self,x, y):
        super().__init__()
        self.x = x
        self.y = y
        self.image = pg.Surface((30,30))
        self.rect = self.image.get_rect(center=(x, y))
        pg.draw.circle(self.image, (255,255,0),(15,15), 15)  #半径15の黄色のコイン
        self.image.set_colorkey((0, 0, 0))
        
    def update(self):
        """
        コインと消去の更新に関する関数
        """
        if MV_FIELD == True:
            self.rect.move_ip(-5,0)
        if self.rect.right < 0:
            self.kill()


class Field(pg.sprite.Sprite):
    """
    足場に関するクラス
    """
    def __init__(self,left_L = 100,top_L = HEIGHT-50,yoko = 50,tate = 50, color = (0,0,255)):
        """
        足場のsurfaceを作る関数
        引数：top_L(左上地点x座標),left_L(左上地点y座標),yoko(長さ),tate(高さ)
        """
        super().__init__()
        self.left = left_L
        self.top = top_L
        self.image = pg.Surface((yoko,tate))
        pg.draw.rect(self.image, color,(0,0,yoko,tate))
        self.rect = self.image.get_rect()
        self.rect.centerx = left_L 
        self.rect.centery = top_L

    def update(self):
        """
        足場の移動と消去の更新に関する関数
        """
        if MV_FIELD == True: # フィールドが動いているならオブジェクトを移動させる
            self.rect.move_ip(-5,0)
        if self.rect.right < 0: # 画面外に出たら消去
            self.kill()


def main():
    global MV_FIELD,MV_MOVE
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"{MAIN_DIR}/fig/pg_bg.jpg")
    score = Score()
    bird = Bird(3, (50, 50))
    # bombs = pg.sprite.Group()
    # beams = pg.sprite.Group()
    # exps = pg.sprite.Group()
    #emys = pg.sprite.Group()
    fields = pg.sprite.Group()
    Goal = pg.sprite.Group()
    Goal.add(Field(2500,0,20,HEIGHT))
    coins = pg.sprite.Group()
    for i in range(5):
        coins.add(Coin(random.randint(30, WIDTH), random.randint(50, HEIGHT*0.8)))  #コインの表示
        coins.add(Coin(random.randint(WIDTH, WIDTH*2), random.randint(50, HEIGHT*0.8)))  #スライドさせたときにも表示される
        coins.add(Coin(random.randint(WIDTH*2, WIDTH*3), random.randint(50, HEIGHT*0.8)))
        coins.add(Coin(random.randint(WIDTH*3, GOAL), random.randint(50, HEIGHT*0.8)))
    fields.add(Field())
    Death_fields = pg.sprite.Group()
    Death_fields.add(Field(100,HEIGHT-50,50,50,(255,0,0)))
    # fields.add(Field())
    fields.add(Field(0,HEIGHT-20,1000,20))
    fields.add(Field(1200,HEIGHT-20,200,20))
    fields.add(Field(1000,HEIGHT/2))



    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            # if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
            #     beams.add(Beam(bird))

        screen.blit(bg_img, [0, 0])

        #if tmr%100 == 0:  # 200フレームに1回，敵機を出現させる
        #     emys.add(Enemy())

        # for emy in emys:
        #     if emy.state == "stop" and tmr%emy.interval == 0:
        #         # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
        #         bombs.add(Bomb(emy, bird))

        # for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
        #     exps.add(Explosion(emy, 100))  # 爆発エフェクト
        #     score.value += 10  # 10点アップ
        #     bird.change_img(6, screen)  # こうかとん喜びエフェクト

        # for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
        #     exps.add(Explosion(bomb, 50))  # 爆発エフェクト
        #     score.value += 1  # 1点アップ
             
        if pg.sprite.spritecollide(bird, coins, True): 
             score.value += 100     

               

        #if len(pg.sprite.spritecollide(bird, emys, True)) != 0:
        #     bird.change_img(8, screen) # こうかとん悲しみエフェクト
             #score.update(screen)
             #score.value += 100  # 1点アップ
        #     pg.display.update()
        #     time.sleep(2)
        

        if pg.sprite.spritecollide(bird, Death_fields, True): # 即死オブジェクト判定
            bird.change_img(8, screen) # こうかとん悲しみエフェクト
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return

        if pg.sprite.spritecollide(bird,fields,False):
            cc = pg.sprite.spritecollideany(bird,fields)
            print(cc.rect.center)
            if cc.rect.centery+20 <= bird.rect.top <= cc.rect.bottom:#フィールドオブジェクトの上面判定
                bird.rect.move_ip(0,10) # 物体に対する反発
            if cc.rect.top <= bird.rect.bottom <= cc.rect.centery+20:#フィールドオブジェクトの下面判定
                bird.rect.move_ip(0,-12) # 物体に対する反発
            bird.rect.move_ip(0,-2) # 重力付与
            MV_MOVE = True

        if bird.rect.top < 1 or HEIGHT -1 < bird.rect.bottom: # 上下画面外判定
            bird.change_img(8, screen) # こうかとん悲しみエフェクト
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return
        
        if len(pg.sprite.spritecollide(bird,Goal,False)) != 0:
            bird.change_img(6, screen) # こうかとん嬉しいエフェクト
            score.update(screen)
            pg.display.update()
            time.sleep(2)
            return

        bird.update(key_lst, screen)
        # beams.update()
        # beams.draw(screen)
        #emys.update()
        #emys.draw(screen)
        # bombs.update()
        # bombs.draw(screen)
        # exps.update()
        # exps.draw(screen)
        Goal.update()
        Goal.draw(screen)
        fields.update()
        fields.draw(screen)
        Death_fields.update()
        Death_fields.draw(screen)
        coins.update()
        coins.draw(screen)
        score.update(screen)
        pg.display.update()
        MV_FIELD = False
        MV_MOVE = False
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
