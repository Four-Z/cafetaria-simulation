# import packages
import simpy  # framework simulasi
import random  # fungsi untuk menghasilkan bilangan acak
import statistics  # fungsi statistika untuk melakukan perhitungan
import itertools  # fungsi untuk membuat dan mengolah iterasi dan kombinasi data
import numpy as np  # komputasi numerik

# SEED FOR EVERY STREAMS
# random seed untuk waktu kedatangan (stream 1)
SEED_INTERVAL_TIME = 100
# random seed untuk ukuran grup (stream 2)
SEED_GROUP_SIZE = 200
# random seed untuk pemilihan rute (stream 3)
SEED_ROUTE_CHOICE = 300
# random seed untuk waktu pelayanan hotfood (stream 4)
SEED_ST_HOT_FOOD = 400
# random seed untuk waktu pelayanan sandwich (stream 5)
SEED_ST_SANDWICH = 500
# random seed untuk waktu pelayanan drinks (stream 6)
SEED_ST_DRINKS = 600
# random seed untuk akumulasi waktu kasir hotfood (stream 7)
SEED_ACT_HOT_FOOD = 700
# random seed untuk akumulasi waktu kasir sandwich (stream 8)
SEED_ACT_SANDWICH = 800
# random seed untuk akumulasi waktu kasir hotfood (stream 9)
SEED_ACT_DRINKS = 900

# Parameter Configuration
NUM_HOT_FOOD_EMPLOYEE = 1  # jumlah pelayan hotfood
NUM_SANDWICH_EMPLOYEE = 1  # jumlah pelayan sandwich
NUM_CASHIER = 2  # jumlah kasir

# Parameter Duration
SIMULATION_DURATION = 5400  # #waktu simulasi (detik)
# waktu antar kedatangan ukuran grup menyebar eksponensial dengan rata-rata 30 detik
INTERVAL_CUSTOMER_ARRIVAL = 30


# Objek Pelanggan yang berinteraksi dengan semua layanan pada cafetaria
class Pelanggan:
    def __init__(self, customer_id, route, group_size):
        self.customer_id = customer_id
        self.route = route
        self.group_size = group_size

        self.hot_food_enter_time = 0  # waktu masuk antrian hotfood
        self.specialty_sandwich_enter_time = 0  # waktu masuk antrian sandwich
        self.cashier_enter_time = 0  # waktu masuk antrian drinks

        self.hot_food_time = 0  # delay pada antrian hotfood
        self.sandwich_time = 0  # delay pada antrian sandwich

        # jika false masih delay di antrian
        self.hot_food_finish_queue = False
        self.specialty_sandwich_finish_queue = False
        self.cashier_finish_queue = False

        self.accumulated_cashier_time = 0
        self.cashier_time = 0  # delay pada antrian cashier


# Urutan pengerjaan cafetaria : inisialisasi stasiun, setup simulasi, menjalankan simulasi, laporan simulasi
def cafeteria_simulation(env):
    hot_food = HotFoodStation(env, NUM_HOT_FOOD_EMPLOYEE)
    sandwich = SpecialtySandwichStation(env, NUM_SANDWICH_EMPLOYEE)
    drinks = DrinksStation(env)
    cashier = CashierStation(env, NUM_CASHIER)

    # Menyimpan seluruh customers yang datang, untuk menghitung statistik
    customers = []

    # Dictionary untuk menyimpan waktu panjang antrian
    lengths_queue = {"hot-food": {},
                     "sandwich": {},
                     "cashiers": {}}

    # Proses cafetaria sampai waktu simulasi berakhir
    env.process(setup(env, lengths_queue, hot_food, sandwich, drinks,
                cashier, customers, INTERVAL_CUSTOMER_ARRIVAL))

    env.run(until=SIMULATION_DURATION)

    print("------------------------------------")
    print(f'TOTAL CUSTOMERS: {len(customers)}')
    print("------------------------------------")

    # Laporan simulasi
    generate_report(customers, lengths_queue)


# Inisiasi pemilihan ukuran grup dan rutes
def setup(env, lengths_queue, hot_food, sandwich, drink, cashier, customers, time_interval):
    group_count = itertools.count()

    group_size = random.Random(SEED_GROUP_SIZE + next(group_count)).choices(
        [1, 2, 3, 4], weights=[0.5, 0.3, 0.1, 0.1])[0]  # pemilihan ukuran grup
    customer_count = itertools.count()  # urutan bilangan bulat untuk customer

    # Buat pelanggan individu sesuai ukuran group
    for _ in range(group_size):
        customer_id = next(customer_count) + 1
        route = random.Random(
            SEED_ROUTE_CHOICE + customer_id).choices([1, 2, 3], weights=[0.8, 0.15, 0.05])[0]
        # bikin setiap customer sesuai jumlah groupnya
        customer = Pelanggan(customer_id, route, group_size)
        # masukkan customer kedalam list customers yang diatas
        customers.append(customer)
        print(
            f'Pelanggan {customer.customer_id} TIBA di Cafetaria pada waktu {env.now:.2f}')
        env.process(process_customer(env, lengths_queue, customer,
                    hot_food, sandwich, drink, cashier))

    # Pelanggan Datang selama waktu simulasi berjalan
    while True:
        group_size = random.Random(SEED_GROUP_SIZE + next(group_count)
                                   ).choices([1, 2, 3, 4], weights=[0.5, 0.3, 0.1, 0.1])[0]

        # Waktu antar kedatangan ukuran grup menyebar eksponensial dengan rata-rata 30 detik
        time_interval = np.random.RandomState(
            SEED_INTERVAL_TIME + next(group_count)).exponential(scale=30)
        # waktu tunggu antar kedatangan pelanggan menyebar eksponensial 30 detik
        yield env.timeout(time_interval)

        for _ in range(group_size):
            customer_id = next(customer_count) + 1
            route = random.Random(
                SEED_ROUTE_CHOICE + customer_id).choices([1, 2, 3], weights=[0.8, 0.15, 0.05])[0]
            customer = Pelanggan(customer_id, route, group_size)
            customers.append(customer)
            print(
                f'Pelanggan {customer.customer_id} TIBA di Cafetaria pada waktu {env.now:.2f}')
            env.process(process_customer(env, lengths_queue, customer,
                        hot_food, sandwich, drink, cashier))


def cs(env, lengths_queue, customer, station_name, station):
    ## FOR DRINK ##
    if station_name == 'drink':
        print(
            f'Pelanggan {customer.customer_id} DILAYANI di stasiun {station_name} pada waktu {env.now:.2f}')

        yield env.process(station.service(customer))
        print(
            f'Pelanggan {customer.customer_id} MENINGGALKAN {station_name} pada waktu {env.now:.2f}')
        return

    print(
        f"Pelanggan {customer.customer_id} Mulai MENGANTRI di Station {station_name} pada {env.now:.2f}.")

    ## FOR CASHIER ##
    if station_name == 'cashier':
        index_shortest_queue = station.find_shortest_queue()
        with station.queues[index_shortest_queue].request() as request:
            customer.cashier_enter_time = env.now
            if len(station.queues[index_shortest_queue].queue) not in lengths_queue["cashiers"]:
                lengths_queue["cashiers"][len(station.queues[index_shortest_queue].queue)
                                          ] = customer.cashier_enter_time - station.queue_change_time
            else:
                lengths_queue["cashiers"][len(station.queues[index_shortest_queue].queue)
                                          ] += customer.cashier_enter_time - station.queue_change_time

            # Waktu customer masuk antrian
            station.queue_change_time = env.now
            yield request
            print(
                f'Pelanggan {customer.customer_id} DILAYANI di {station_name} pada waktu {env.now:.2f}')

            yield env.process(station.service(customer, lengths_queue, index_shortest_queue))
            print(
                f'Pelanggan {customer.customer_id} MENINGGALKAN {station_name} pada waktu {env.now:.2f}')
            return

     ## FOR HOT FOOD & SANDWICH ##
    with station.queue.request() as request:

        # SET STATION ENTER QUEUE TIME
        if station_name == 'hot-food':
            customer.hot_food_enter_time = env.now
            # print(f"MASUK ANTRIAN HOT-FOOD: {len(station.queue.queue)}")

            if len(station.queue.queue) not in lengths_queue["hot-food"]:
                lengths_queue["hot-food"][len(station.queue.queue)
                                          ] = customer.hot_food_enter_time - station.queue_change_time
            else:
                lengths_queue["hot-food"][len(station.queue.queue)
                                          ] += customer.hot_food_enter_time - station.queue_change_time

        elif station_name == 'sandwich':
            customer.specialty_sandwich_enter_time = env.now
            # print(f"MASUK ANTRIAN SANDWICH: {len(station.queue.queue)}")

            if len(station.queue.queue) not in lengths_queue["sandwich"]:
                lengths_queue["sandwich"][len(station.queue.queue)
                                          ] = customer.specialty_sandwich_enter_time - station.queue_change_time
            else:
                lengths_queue["sandwich"][len(station.queue.queue)
                                          ] += customer.specialty_sandwich_enter_time - station.queue_change_time

        # Waktu customer masuk antrian
        station.queue_change_time = env.now

        yield request
        # req aja kaya membuka gitu
        print(
            f'Pelanggan {customer.customer_id} DILAYANI di stasiun {station_name} pada waktu {env.now:.2f}')

        yield env.process(station.service(customer, lengths_queue))

        print(
            f'Pelanggan {customer.customer_id} MENINGGALKAN {station_name} pada waktu {env.now:.2f}')


def process_customer(env, lengths_queue, customer, hot_food, sandwich, drink, cashier):
    if customer.route == 1:
        yield env.process(cs(env, lengths_queue, customer, 'hot-food', hot_food))
        # print(f"MENINGGALKAN STATION HOT-FOOD: {len(hot_food.queue.queue)}")
        yield env.process(cs(env, lengths_queue, customer, 'drink', drink))
        yield env.process(cs(env, lengths_queue, customer, 'cashier', cashier))
        # print(f"MENINGGALKAN CASHIER: {len(cashier.queue.queue)}")
    elif customer.route == 2:
        yield env.process(cs(env, lengths_queue, customer, 'sandwich', sandwich))
        # print(f"MENINGGALKAN STATION SANDWICH: {len(sandwich.queue.queue)}")
        yield env.process(cs(env, lengths_queue, customer, 'drink', drink))
        yield env.process(cs(env, lengths_queue, customer, 'cashier', cashier))
        # print(f"MENINGGALKAN CASHIER: {len(cashier.queue.queue)}")
    elif customer.route == 3:
        yield env.process(cs(env, lengths_queue, customer, 'drink', drink))
        yield env.process(cs(env, lengths_queue, customer, 'cashier', cashier))
        # print(f"MENINGGALKAN CASHIER: {len(cashier.queue.queue)}")


class HotFoodStation:
    def __init__(self, env, NUM_HOT_FOOD_EMPLOYEE):
        self.NUM_HOT_FOOD_EMPLOYEE = NUM_HOT_FOOD_EMPLOYEE
        self.env = env
        self.queue = simpy.Resource(env, capacity=1)
        self.queue_change_time = 0

    def service(self, customer, lengths_queue):
        # Menghitung Lama Menunggu Antrian
        # delay = waktu dilakukan service - waktu pelanggan masuk antrian hotfood
        delay = self.env.now - customer.hot_food_enter_time
        customer.hot_food_time = delay
        customer.hot_food_finish_queue = True  # jika true, pelanggan dilayani
        print(
            f'Pelanggan {customer.customer_id} DELAY di antrian hotfood pada waktu {delay:.2f}')

        # service time menyebar uniform (50,120)
        service_time_start = 50.0/self.NUM_HOT_FOOD_EMPLOYEE
        service_time_end = 120.0/self.NUM_HOT_FOOD_EMPLOYEE
        service_time = random.Random(
            SEED_ST_HOT_FOOD + customer.customer_id).uniform(service_time_start, service_time_end)

        if len(self.queue.queue) not in lengths_queue["hot-food"]:
            lengths_queue["hot-food"][int(len(self.queue.queue))
                                      ] = self.env.now - self.queue_change_time
        else:
            # print(f"NOW = {self.env.now}")
            # print(f"T = {self.queue_change_time}")

            lengths_queue["hot-food"][len(self.queue.queue)
                                      ] += self.env.now - self.queue_change_time

        # Waktu customer keluar antrian
        self.queue_change_time = self.env.now

        # untuk memajukan waktu sebanyak waktu pelayanan
        yield self.env.timeout(service_time)

        accumulated_cashier_time = random.Random(
            SEED_ACT_HOT_FOOD + customer.customer_id).uniform(20.0, 40.0)
        customer.accumulated_cashier_time += accumulated_cashier_time


class SpecialtySandwichStation:
    def __init__(self, env, NUM_SANDWICH_EMPLOYEE):
        self.NUM_SANDWICH_EMPLOYEE = NUM_SANDWICH_EMPLOYEE
        self.env = env
        self.queue = simpy.Resource(env, capacity=1)
        self.queue_change_time = 0

    def service(self, customer, lengths_queue):
        # Menghitung Lama Menunggu Antrian
        # delay = waktu dilakukan service - waktu pelanggan masuk antrian sandwich
        delay = self.env.now - customer.specialty_sandwich_enter_time
        customer.sandwich_time = delay
        customer.specialty_sandwich_finish_queue = True  # jika true, pelanggan dilayani
        print(
            f'Pelanggan {customer.customer_id} DELAY di antrian sandwich pada waktu {delay:.2f}')

        # service time menyebar uniform (60,180)
        service_time_start = 60.0/self.NUM_SANDWICH_EMPLOYEE
        service_time_end = 180.0/self.NUM_SANDWICH_EMPLOYEE
        service_time = random.Random(
            SEED_ST_SANDWICH + customer.customer_id).uniform(service_time_start, service_time_end)

        if len(self.queue.queue) not in lengths_queue["sandwich"]:
            lengths_queue["sandwich"][int(len(self.queue.queue))
                                      ] = self.env.now - self.queue_change_time
        else:
            # print(f"NOW = {self.env.now}")
            # print(f"T = {self.queue_change_time}")

            lengths_queue["sandwich"][len(self.queue.queue)
                                      ] += self.env.now - self.queue_change_time

        # Waktu customer keluar antrian
        self.queue_change_time = self.env.now

        yield self.env.timeout(service_time)

        accumulated_cashier_time = random.Random(
            SEED_ACT_SANDWICH + customer.customer_id).uniform(5.0, 15.0)
        customer.accumulated_cashier_time += accumulated_cashier_time


class DrinksStation:
    def __init__(self, env):
        self.env = env

    def service(self, customer):
        # service time menyebar uniform (5,10)
        drink_service_time = random.Random(
            SEED_ST_DRINKS + customer.customer_id).uniform(5.0, 20.0)
        yield self.env.timeout(drink_service_time)

        accumulated_cashier_time = random.Random(
            SEED_ACT_DRINKS + customer.customer_id).uniform(5.0, 10.0)
        customer.accumulated_cashier_time += accumulated_cashier_time


class CashierStation:
    def __init__(self, env, NUM_CASHIER):
        self.env = env
        self.queues = [simpy.Resource(env, capacity=1)
                       for _ in range(NUM_CASHIER)]
        self.queue_change_time = 0

    def service(self, customer, lengths_queue, which_cashier):
        # Menghitung Lama Menunggu Antrian
        # delay = waktu dilakukan service - waktu pelanggan masuk antrian kasir
        delay = self.env.now - customer.cashier_enter_time
        customer.cashier_time = delay
        customer.cashier_finish_queue = True  # jika true, pelanggan dilayani
        print(
            f'Pelanggan {customer.customer_id} DELAY di antrian kasir pada waktu {delay:.2f}')

        cashier_service_time = customer.accumulated_cashier_time

        if len(self.queues[which_cashier].queue) not in lengths_queue["cashiers"]:
            lengths_queue["cashiers"][int(len(self.queue[which_cashier].queue))
                                      ] = self.env.now - self.queue_change_time
        else:
            # print(f"NOW = {self.env.now}")
            # print(f"T = {self.queue_change_time}")

            lengths_queue["cashiers"][len(self.queues[which_cashier].queue)
                                      ] += self.env.now - self.queue_change_time

        # Waktu customer keluar antrian
        self.queue_change_time = self.env.now

        yield self.env.timeout(cashier_service_time)

    def find_shortest_queue(self):
        shortest_queue_index = min(
            range(len(self.queues)), key=lambda i: len(self.queues[i].queue))
        return shortest_queue_index


# Laporan statistik
def report_1(customers):
    # Menghitung pelanggan yang sudah dilayani di masing-masing stasiun
    hot_food_delays = [customer.hot_food_time for customer in customers if customer.route ==
                       1 and customer.hot_food_finish_queue]
    sandwich_delays = [customer.sandwich_time for customer in customers if customer.route ==
                       2 and customer.specialty_sandwich_finish_queue]
    cashier_delays = [
        customer.cashier_time for customer in customers if customer.cashier_finish_queue]

    # Max delay untuk stasiun hot food
    hot_food_max_delay = max(hot_food_delays)

    # Max delay untuk stasiun sandwich
    sandwich_max_delay = max(sandwich_delays)

    # Max delay untuk stasiun kasir
    cashier_max_delay = max(cashier_delays)

    # Hitung total waktu delay per station
    total_delay_time_hot_food = sum(hot_food_delays)
    total_delay_time_sandwich = sum(sandwich_delays)
    total_delay_time_cashiers = sum(cashier_delays)

    # Hitung total pelanggan yang mengalami delay per station
    total_delayed_customers_hot_food = len(hot_food_delays)
    total_delayed_customers_sandwich = len(sandwich_delays)
    total_delayed_customers_cashiers = len(cashier_delays)

    # Hitung rata-rata delay per orang per station
    avg_delay_per_person_hot_food = total_delay_time_hot_food / \
        total_delayed_customers_hot_food

    avg_delay_per_person_sandwich = total_delay_time_sandwich / \
        total_delayed_customers_sandwich

    avg_delay_per_person_cashiers = total_delay_time_cashiers / \
        total_delayed_customers_cashiers

    # Menampilkan hasil laporan
    print("1. Rata-rata dan maksimum delay antrian untuk Hot-Food, Specialty Sandwiches, dan Kasir (Terlepas dari kasir mana)")
    print(f"\nMetrik Hot Food:")
    print(f"  Rata-rata Delay: {avg_delay_per_person_hot_food:.2f} Detik")
    print(f"  Maksimum Delay : {hot_food_max_delay:.2f} Detik")

    print(f"\nMetrik Specialty Sandwich:")
    print(f"  Rata-rata Delay: {avg_delay_per_person_sandwich:.2f} Detik")
    print(f"  Maksimum Delay : {sandwich_max_delay:.2f} Detik")

    print(f"\nMetrik Kasir:")
    print(f"  Rata-rata Delay: {avg_delay_per_person_cashiers:.2f} Detik")
    print(f"  Maksimum Delay : {cashier_max_delay:.2f} Detik")


def report_2(lengths_queue):
    print(lengths_queue)
    # Calculate Time Average in Queue for Hot-Food Station
    pembilang_hot_food = 0
    penyebut_hot_food = 0
    for key in lengths_queue["hot-food"]:
        pembilang_hot_food += (key * lengths_queue["hot-food"][key])
        penyebut_hot_food += lengths_queue["hot-food"][key]

    # Calculate Time Average in Queue for Specialty Sandwich Station
    pembilang_sandwich = 0
    penyebut_sandwich = 0
    for key in lengths_queue["sandwich"]:
        pembilang_sandwich += (key * lengths_queue["sandwich"][key])
        penyebut_sandwich += lengths_queue["sandwich"][key]

    # Calculate Time Average in Queue for Cashiers
    pembilang_cashiers = 0
    penyebut_cashiers = 0
    for key in lengths_queue["cashiers"]:
        pembilang_cashiers += (key * lengths_queue["cashiers"][key])
        penyebut_cashiers += lengths_queue["cashiers"][key]

    # Metrik for All Station
    time_avg_queue_hot_food = pembilang_hot_food/penyebut_hot_food
    max_queue_customer_hot_food = list(lengths_queue["hot-food"].keys())[-1]

    time_avg_queue_sandwich = pembilang_sandwich/penyebut_sandwich
    max_queue_customer_sandwich = list(lengths_queue["sandwich"].keys())[-1]

    time_avg_queue_cashiers = pembilang_cashiers/penyebut_cashiers
    max_queue_customer_cashiers = list(lengths_queue["cashiers"].keys())[-1]

    # Menampilkan hasil laporan
    print("\n\n2. Rata-rata waktu dan jumlah maksimum dalam antrian untuk Hot Food dan Specialty Sandwiches (terpisah), serta rata-rata waktu dan jumlah maksimum total dalam semua antrian kasir")
    print(f"\nMetrik Hot Food:")
    print(
        f"  Rata-rata Waktu di Antrian: {time_avg_queue_hot_food:.2f} Detik")
    print(
        f"  Maksimum Antrian:  {max_queue_customer_hot_food} Customer")

    print(f"\nMetrik Specialty Sandwich:")
    print(
        f"  Rata-rata Waktu di Antrian: {time_avg_queue_sandwich:.2f} Detik")
    print(
        f"  Maksimum Antrian:  {max_queue_customer_sandwich} Customer")

    print(f"\nMetrik Cashiers:")
    print(
        f"  Rata-rata Waktu di Antrian: {time_avg_queue_cashiers:.2f} Detik")
    print(
        f"  Maksimum Antrian:  {max_queue_customer_cashiers} Customer")


def report_3(customers):
    # Menghitung pelanggan yang sudah dilayani di masing-masing stasiun
    route_1_delays = [customer.hot_food_time+customer.cashier_time for customer in customers if customer.route ==
                      1 and customer.hot_food_finish_queue and customer.cashier_finish_queue]
    route_2_delays = [customer.sandwich_time+customer.cashier_time for customer in customers if customer.route ==
                      2 and customer.specialty_sandwich_finish_queue and customer.cashier_finish_queue]
    route_3_delays = [
        customer.cashier_time for customer in customers if customer.route == 3 and customer.cashier_finish_queue]

    # Max delay untuk rute 1
    route_1_max_delay = max(route_1_delays)

    # Max delay untuk rute 2
    route_2_max_delay = max(route_2_delays)

    # Max delay untuk rute 3
    route_3_max_delay = max(route_3_delays)

    # Hitung total waktu delay per rute
    total_delay_time_route_1 = sum(route_1_delays)
    total_delay_time_route_2 = sum(route_2_delays)
    total_delay_time_route_3 = sum(route_3_delays)

    # Hitung total pelanggan yang mengalami delay per rute
    total_delayed_customers_route_1 = len(route_1_delays)
    total_delayed_customers_route_2 = len(route_2_delays)
    total_delayed_customers_route_3 = len(route_3_delays)

    # Hitung rata-rata delay per orang per rute
    avg_delay_per_person_route_1 = total_delay_time_route_1 / \
        total_delayed_customers_route_1

    avg_delay_per_person_route_2 = total_delay_time_route_2 / \
        total_delayed_customers_route_2

    avg_delay_per_person_route_3 = total_delay_time_route_3 / \
        total_delayed_customers_route_3

    # Menampilkan hasil laporan
    print("\n\n3. Rata-rata dan maksimum total delay dalam semua antrian untuk masing-masing tipe pelanggan (terpisah)")
    print(f"\nMetrik Rute 1:")
    print(
        f"  Rata-rata Delay: {avg_delay_per_person_route_1:.2f} Detik")
    print(f"  Maksimum Delay dalam Antrian: {route_1_max_delay:.2f} Detik")

    print(f"\nMetrik Rute 2:")
    print(
        f"  Rata-rata Delay: {avg_delay_per_person_route_2:.2f} Detik")
    print(f"  Maksimum Delay dalam Antrian: {route_2_max_delay:.2f} Detik")

    print(f"\nMetrik Rute 3:")
    print(
        f"  Rata-rata Delay: {avg_delay_per_person_route_3:.2f} Detik")
    print(f"  Maksimum Delay dalam Antrian: {route_3_max_delay:.2f} Detik")


def report_4(customers):
    # Mengelompokkan pelanggan berdasarkan ukuran grup
    customers_group = {1: [], 2: [], 3: [], 4: []}

    def calculate_time(customer):
        # Menghitung total waktu delay berdasarkan rute pelanggan
        if customer.route == 1:
            return customer.hot_food_time + customer.cashier_time
        elif customer.route == 2:
            return customer.sandwich_time + customer.cashier_time
        elif customer.route == 3:
            return customer.cashier_time

    # Memisahkan pelanggan berdasarkan ukuran grup dan menghitung waktu delaynya
    for customer in customers:
        if customer.cashier_finish_queue:
            customers_group[customer.group_size].append(
                calculate_time(customer))

    # Mencari rata-rata per grup
    group_avgs = {group_size: statistics.mean(
        delays) for group_size, delays in customers_group.items()}

    # Rata-rata total terponderasi
    overall_avg = (
        0.5 * group_avgs.get(1, 0) +
        0.3 * group_avgs.get(2, 0) +
        0.1 * group_avgs.get(3, 0) +
        0.1 * group_avgs.get(4, 0)
    )

    # Menampilkan hasil laporan
    print("\n\n4. Rata-rata total delay untuk semua pelanggan, ditemukan dengan memberikan bobot rata-rata total delay individu mereka dengan probabilitas masing-masing kemunculan")
    print(f"\nRata-rata Keseluruhan: {overall_avg:.2f} Detik")


def report_5(customers, lengths_queue):
    # Calculate Time Average in Queue for Hot-Food Station
    pembilang_hot_food = 0
    penyebut_hot_food = 0
    for key in lengths_queue["hot-food"]:
        pembilang_hot_food += (key * lengths_queue["hot-food"][key])
        penyebut_hot_food += lengths_queue["hot-food"][key]

    # Calculate Time Average in Queue for Specialty Sandwich Station
    pembilang_sandwich = 0
    penyebut_sandwich = 0
    for key in lengths_queue["sandwich"]:
        pembilang_sandwich += (key * lengths_queue["sandwich"][key])
        penyebut_sandwich += lengths_queue["sandwich"][key]

    # Calculate Time Average in Queue for Cashiers
    pembilang_cashiers = 0
    penyebut_cashiers = 0
    for key in lengths_queue["cashiers"]:
        pembilang_cashiers += (key * lengths_queue["cashiers"][key])
        penyebut_cashiers += lengths_queue["cashiers"][key]

    # Metrik All Station
    time_avg_delay_hot_food = pembilang_hot_food/penyebut_hot_food
    time_avg_delay_sandwich = pembilang_sandwich/penyebut_sandwich
    time_avg_delay_cashiers = pembilang_cashiers/penyebut_cashiers

    # Calculate Time Average Queue in The Entire System
    time_avg_all_station = statistics.mean(
        [time_avg_delay_hot_food, time_avg_delay_sandwich, time_avg_delay_cashiers])

    # Menampilkan hasil laporan
    print("\n\n5. Rata-rata total delay dan jumlah maksimum pelanggan di seluruh sistem (for reporting to the fire marshall)")
    print(
        f"\nRata-rata Waktu Antrian di Seluruh Sistem: {time_avg_all_station:.2f} Detik")
    print(
        f"Jumlah Maksimum Pelanggan di Seluruh Sistem: {len(customers)} Pelanggan")


def generate_report(customers, lengths_queue):
    print("\n------------------- REPORT -------------------\n")

    report_1(customers)
    report_2(lengths_queue)
    report_3(customers)
    report_4(customers)
    report_5(customers, lengths_queue)

    print("\n----------------------------------------------")


def run_simulation():
    env = simpy.Environment()
    cafeteria_simulation(env)


# START PROGRAM
run_simulation()
